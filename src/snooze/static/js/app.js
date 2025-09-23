// Main JavaScript for Snooze application

class SnoozeApp {
    constructor() {
        this.socket = null;
        this.useAsync = true; // Toggle between async and sync analysis
        this.realTimePostsReceived = 0;
        this.totalPostsExpected = 0;
        this.initializeSocketIO();
        this.initializeEventListeners();
    }

    initializeSocketIO() {
        this.socket = io();

        this.socket.on('connect', () => {
            console.log('Connected to server');
        });

        this.socket.on('progress', (data) => {
            this.updateProgress(data);
        });

        this.socket.on('post_summary_ready', (data) => {
            this.addRealTimePost(data);
        });

        this.socket.on('analysis_complete', (data) => {
            this.hideLoading();
            this.displayResults(data);
        });

        this.socket.on('error', (data) => {
            this.hideLoading();
            this.showError(data.message);
        });
    }

    initializeEventListeners() {
        const analyzeForm = document.getElementById('analyzeForm');
        if (analyzeForm) {
            analyzeForm.addEventListener('submit', (e) => this.handleAnalyze(e));
        }
    }

    async handleAnalyze(event) {
        event.preventDefault();

        const subredditsInput = document.getElementById('subreddits').value;
        const limitInput = document.getElementById('limit').value;

        const subreddits = subredditsInput.split(',').map(s => s.trim()).filter(s => s);
        const limit = parseInt(limitInput) || 20;

        this.realTimePostsReceived = 0;
        this.totalPostsExpected = 0;

        this.showLoading();
        this.hideResults();
        this.hideError();
        this.clearRealTimeResults();

        // Disable the analyze button
        const analyzeBtn = document.getElementById('analyzeBtn');
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Analyzing...';

        try {
            if (this.useAsync) {
                // Use the new async endpoint with real-time updates
                const response = await fetch('/api/analyze-async', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        subreddits: subreddits,
                        limit: limit
                    })
                });

                const data = await response.json();
                if (!data.success) {
                    this.showError(data.error || 'Failed to start analysis');
                    this.resetAnalyzeButton();
                }
                // Real-time updates will be handled via WebSocket
            } else {
                // Fallback to synchronous analysis
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        subreddits: subreddits,
                        limit: limit
                    })
                });

                const data = await response.json();

                if (data.success && data.discussion) {
                    this.displayResults(data);
                } else {
                    this.showError(data.error || 'Analysis failed');
                }
                this.hideLoading();
                this.resetAnalyzeButton();
            }
        } catch (error) {
            this.showError(`Network error: ${error.message}`);
            this.hideLoading();
            this.resetAnalyzeButton();
        }
    }

    resetAnalyzeButton() {
        const analyzeBtn = document.getElementById('analyzeBtn');
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = '<i class="fas fa-play me-2"></i>Analyze';
    }

    updateProgress(data) {
        const progressMessage = document.getElementById('progressMessage');
        progressMessage.textContent = data.message;

        if (data.stage === 'posts_ready') {
            this.totalPostsExpected = data.post_count;
            const progressBar = document.getElementById('progressBar');
            progressBar.style.display = 'block';
        }
    }

    addRealTimePost(data) {
        this.realTimePostsReceived++;

        // Update progress bar
        if (this.totalPostsExpected > 0) {
            const percentage = (this.realTimePostsReceived / this.totalPostsExpected) * 100;
            const progressBar = document.querySelector('.progress-bar');
            progressBar.style.width = `${percentage}%`;
            progressBar.textContent = `${this.realTimePostsReceived}/${this.totalPostsExpected}`;
        }

        // Show real-time results section
        const realTimeResults = document.getElementById('realTimeResults');
        realTimeResults.style.display = 'block';

        // Add the post to real-time list
        const postList = document.getElementById('realTimePostList');
        const postElement = this.createRealTimePostElement(data.summary);
        postList.appendChild(postElement);

        // Scroll to the new post
        postElement.scrollIntoView({ behavior: 'smooth' });
    }

    createRealTimePostElement(summary) {
        const div = document.createElement('div');
        div.className = 'real-time-post mb-3 p-3 border rounded shadow-sm';
        div.innerHTML = `
            <div class="d-flex justify-content-between align-items-start mb-2">
                <h6 class="mb-0">
                    <a href="${summary.url}" target="_blank" class="text-decoration-none text-primary">
                        <i class="fas fa-external-link-alt me-1"></i>${summary.title}
                    </a>
                </h6>
                <div class="d-flex gap-2 align-items-center">
                    <span class="badge bg-secondary">r/${summary.subreddit}</span>
                    <span class="sentiment-badge sentiment-${summary.sentiment} badge">
                        ${this.getSentimentIcon(summary.sentiment)} ${summary.sentiment}
                    </span>
                </div>
            </div>

            <p class="text-muted mb-2">${summary.summary}</p>

            <div class="mb-2">
                <strong class="text-dark">Topics:</strong>
                <div class="mt-1">
                    ${summary.topics.map(topic =>
                        `<div class="key-point d-flex align-items-start mb-1">
                            <i class="fas fa-chevron-right text-success me-2 mt-1" style="font-size: 0.7em;"></i>
                            <span class="small">${topic}</span>
                        </div>`
                    ).join('')}
                </div>
            </div>

            <div class="mb-2">
                <strong class="text-dark">Key Points:</strong>
                <div class="mt-1">
                    ${summary.key_points.map(point =>
                        `<div class="key-point d-flex align-items-start mb-1">
                            <i class="fas fa-chevron-right text-primary me-2 mt-1" style="font-size: 0.7em;"></i>
                            <span class="small">${point}</span>
                        </div>`
                    ).join('')}
                </div>
            </div>

            <div class="d-flex gap-3 small text-muted">
                <span><i class="fas fa-calendar me-1"></i>${this.formatPostDate(summary.created_utc)}</span>
                <span><i class="fas fa-arrow-up me-1"></i>${summary.score || 0} upvotes</span>
                <span><i class="fas fa-comments me-1"></i>${summary.num_comments || 0} comments</span>
                <span><i class="fas fa-star me-1"></i>${summary.engagement_score}/10</span>
            </div>
        `;
        return div;
    }

    clearRealTimeResults() {
        document.getElementById('realTimePostList').innerHTML = '';
        document.getElementById('realTimeResults').style.display = 'none';
        document.getElementById('progressBar').style.display = 'none';
    }

    showLoading() {
        document.getElementById('loadingState').style.display = 'block';
    }

    hideLoading() {
        document.getElementById('loadingState').style.display = 'none';
    }

    showResults() {
        document.getElementById('resultsSection').style.display = 'block';
    }

    hideResults() {
        document.getElementById('resultsSection').style.display = 'none';
    }

    showError(message) {
        document.getElementById('errorMessage').textContent = message;
        document.getElementById('errorState').style.display = 'block';
    }

    hideError() {
        document.getElementById('errorState').style.display = 'none';
    }

    displayResults(data) {
        const discussion = data.discussion;

        // Update overview
        document.getElementById('discussionTopic').textContent = discussion.topic;
        document.getElementById('sentimentOverview').textContent = discussion.sentiment_overview;
        document.getElementById('postCount').textContent = data.post_count || 0;
        document.getElementById('keptPostsCount').textContent = discussion.total_posts_analyzed || 0;
        document.getElementById('engagementScore').textContent = discussion.total_engagement;

        // Display key insights
        this.displayKeyInsights(discussion.key_insights);

        // Display common themes
        this.displayCommonThemes(discussion.common_themes);

        // Display post summaries
        this.displayPostSummaries(discussion.post_summaries);

        this.showResults();
        this.resetAnalyzeButton();
    }

    displayKeyInsights(insights) {
        const container = document.getElementById('keyInsights');
        container.innerHTML = '';

        insights.forEach(insight => {
            const li = document.createElement('li');
            li.className = 'insight-item';
            li.innerHTML = `<i class="fas fa-arrow-right me-2 text-success"></i>${insight}`;
            container.appendChild(li);
        });
    }

    displayCommonThemes(themes) {
        const container = document.getElementById('commonThemes');
        container.innerHTML = '';

        themes.forEach(theme => {
            const span = document.createElement('span');
            span.className = 'theme-tag';
            span.textContent = theme;
            container.appendChild(span);
        });
    }

    displayPostSummaries(summaries) {
        const container = document.getElementById('postSummaries');
        container.innerHTML = '';

        summaries.forEach(summary => {
            const div = document.createElement('div');
            div.className = 'post-summary mb-3 p-3 border rounded shadow-sm';

            div.innerHTML = `
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h6 class="mb-0">
                        <a href="${summary.url}" target="_blank" class="text-decoration-none text-primary">
                            <i class="fas fa-external-link-alt me-1"></i>${summary.title}
                        </a>
                    </h6>
                    <div class="d-flex gap-2 align-items-center">
                        <span class="badge bg-secondary">r/${summary.subreddit}</span>
                        <span class="sentiment-badge sentiment-${summary.sentiment} badge">
                            ${this.getSentimentIcon(summary.sentiment)} ${summary.sentiment}
                        </span>
                    </div>
                </div>

                <p class="text-muted mb-2">${summary.summary}</p>

                <div class="mb-2">
                    <strong class="text-dark">Key Points:</strong>
                    <div class="mt-1">
                        ${summary.key_points.map(point =>
                            `<div class="key-point d-flex align-items-start mb-1">
                                <i class="fas fa-chevron-right text-primary me-2 mt-1" style="font-size: 0.7em;"></i>
                                <span class="small">${point}</span>
                            </div>`
                        ).join('')}
                    </div>
                </div>

                <div class="mb-2">
                    <strong class="text-dark">Topics:</strong>
                    <div class="mt-1">
                        ${summary.topics.map(topic =>
                            `<div class="key-point d-flex align-items-start mb-1">
                                <i class="fas fa-chevron-right text-success me-2 mt-1" style="font-size: 0.7em;"></i>
                                <span class="small">${topic}</span>
                            </div>`
                        ).join('')}
                    </div>
                </div>

                <div class="d-flex gap-3 small text-muted">
                    <span><i class="fas fa-calendar me-1"></i>${this.formatPostDate(summary.created_utc)}</span>
                    <span><i class="fas fa-arrow-up me-1"></i>${summary.score || 0} upvotes</span>
                    <span><i class="fas fa-comments me-1"></i>${summary.num_comments || 0} comments</span>
                    <span><i class="fas fa-star me-1"></i>${summary.engagement_score}/10</span>
                </div>
            `;

            container.appendChild(div);
        });
    }

    getSentimentIcon(sentiment) {
        switch (sentiment.toLowerCase()) {
            case 'positive':
                return '<i class="fas fa-smile"></i>';
            case 'negative':
                return '<i class="fas fa-frown"></i>';
            case 'mixed':
                return '<i class="fas fa-meh"></i>';
            default:
                return '<i class="fas fa-meh"></i>';
        }
    }

    formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleString();
    }

    formatPostDate(created_utc) {
        if (!created_utc) return 'Unknown date';

        const date = new Date(created_utc);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

        if (diffDays === 1) {
            return 'Yesterday';
        } else if (diffDays <= 7) {
            return `${diffDays} days ago`;
        } else if (diffDays <= 30) {
            const weeks = Math.floor(diffDays / 7);
            return weeks === 1 ? '1 week ago' : `${weeks} weeks ago`;
        } else {
            return date.toLocaleDateString();
        }
    }
}

// Initialize the app when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new SnoozeApp();
});