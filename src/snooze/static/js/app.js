// Main JavaScript for Snooze application

class SnoozeApp {
    constructor() {
        this.initializeEventListeners();
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

        this.showLoading();
        this.hideResults();
        this.hideError();

        try {
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
        } catch (error) {
            this.showError(`Network error: ${error.message}`);
        } finally {
            this.hideLoading();
        }
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
        document.getElementById('postCount').textContent = data.post_count;
        document.getElementById('engagementScore').textContent = discussion.total_engagement;

        // Display key insights
        this.displayKeyInsights(discussion.key_insights);

        // Display common themes
        this.displayCommonThemes(discussion.common_themes);

        // Display post summaries
        this.displayPostSummaries(discussion.post_summaries);

        this.showResults();
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
            div.className = 'post-summary';

            div.innerHTML = `
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h6 class="mb-0">
                        <a href="${summary.url}" target="_blank" class="text-decoration-none">
                            ${summary.title}
                        </a>
                    </h6>
                    <div class="d-flex gap-2">
                        <span class="subreddit-badge">r/${summary.subreddit}</span>
                        <span class="sentiment-badge sentiment-${summary.sentiment}">
                            ${summary.sentiment}
                        </span>
                        <span class="engagement-score">${summary.engagement_score}/10</span>
                    </div>
                </div>

                <p class="text-muted mb-2">${summary.summary}</p>

                <div class="mb-2">
                    <strong>Key Points:</strong>
                    ${summary.key_points.map(point =>
                        `<div class="key-point">${point}</div>`
                    ).join('')}
                </div>

                <div class="mb-0">
                    <strong>Topics:</strong>
                    ${summary.topics.map(topic =>
                        `<span class="theme-tag">${topic}</span>`
                    ).join('')}
                </div>
            `;

            container.appendChild(div);
        });
    }

    getSentimentIcon(sentiment) {
        switch (sentiment.toLowerCase()) {
            case 'positive':
                return 'fas fa-smile text-success';
            case 'negative':
                return 'fas fa-frown text-danger';
            case 'mixed':
                return 'fas fa-meh text-warning';
            default:
                return 'fas fa-meh text-muted';
        }
    }

    formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleString();
    }
}

// Initialize the app when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new SnoozeApp();
});