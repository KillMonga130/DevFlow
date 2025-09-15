const fs = require('fs').promises;
const path = require('path');

class ModelPerformanceTracker {
  constructor() {
    this.metricsFile = path.join(__dirname, 'model-metrics.json');
    this.metrics = {
      responseTime: [],
      accuracy: [],
      userSatisfaction: [],
      cacheHitRate: 0,
      totalRequests: 0
    };
    this.loadMetrics();
  }

  async loadMetrics() {
    try {
      const data = await fs.readFile(this.metricsFile, 'utf8');
      this.metrics = { ...this.metrics, ...JSON.parse(data) };
    } catch (error) {
      // File doesn't exist yet, use defaults
      console.log('Starting with fresh metrics tracking');
    }
  }

  async saveMetrics() {
    try {
      await fs.writeFile(this.metricsFile, JSON.stringify(this.metrics, null, 2));
    } catch (error) {
      console.error('Error saving metrics:', error);
    }
  }

  trackResponseTime(startTime, endTime) {
    const responseTime = endTime - startTime;
    this.metrics.responseTime.push({
      time: responseTime,
      timestamp: new Date().toISOString()
    });

    // Keep only last 100 measurements
    if (this.metrics.responseTime.length > 100) {
      this.metrics.responseTime = this.metrics.responseTime.slice(-100);
    }

    this.saveMetrics();
    return responseTime;
  }

  trackAccuracy(userFoundIssues, correctIssues) {
    const accuracy = this.calculateAccuracy(userFoundIssues, correctIssues);
    this.metrics.accuracy.push({
      accuracy,
      timestamp: new Date().toISOString()
    });

    // Keep only last 100 measurements
    if (this.metrics.accuracy.length > 100) {
      this.metrics.accuracy = this.metrics.accuracy.slice(-100);
    }

    this.saveMetrics();
    return accuracy;
  }

  calculateAccuracy(userFound, correct) {
    if (correct.length === 0) return 1.0;
    
    let matches = 0;
    for (const userIssue of userFound) {
      for (const correctIssue of correct) {
        if (Math.abs(userIssue.line - correctIssue.line) <= 2 && 
            userIssue.type === correctIssue.type) {
          matches++;
          break;
        }
      }
    }
    
    return matches / correct.length;
  }

  trackUserSatisfaction(rating, category) {
    this.metrics.userSatisfaction.push({
      rating,
      category,
      timestamp: new Date().toISOString()
    });

    // Keep only last 100 ratings
    if (this.metrics.userSatisfaction.length > 100) {
      this.metrics.userSatisfaction = this.metrics.userSatisfaction.slice(-100);
    }

    this.saveMetrics();
  }

  trackCacheHit(isHit) {
    this.metrics.totalRequests++;
    if (isHit) {
      this.metrics.cacheHitRate = ((this.metrics.cacheHitRate * (this.metrics.totalRequests - 1)) + 1) / this.metrics.totalRequests;
    } else {
      this.metrics.cacheHitRate = (this.metrics.cacheHitRate * (this.metrics.totalRequests - 1)) / this.metrics.totalRequests;
    }
    
    this.saveMetrics();
  }

  getPerformanceReport() {
    const avgResponseTime = this.metrics.responseTime.length > 0 
      ? this.metrics.responseTime.reduce((sum, r) => sum + r.time, 0) / this.metrics.responseTime.length
      : 0;

    const avgAccuracy = this.metrics.accuracy.length > 0
      ? this.metrics.accuracy.reduce((sum, a) => sum + a.accuracy, 0) / this.metrics.accuracy.length
      : 0;

    const avgSatisfaction = this.metrics.userSatisfaction.length > 0
      ? this.metrics.userSatisfaction.reduce((sum, s) => sum + s.rating, 0) / this.metrics.userSatisfaction.length
      : 0;

    return {
      averageResponseTime: Math.round(avgResponseTime),
      averageAccuracy: Math.round(avgAccuracy * 100),
      averageUserSatisfaction: Math.round(avgSatisfaction * 10) / 10,
      cacheHitRate: Math.round(this.metrics.cacheHitRate * 100),
      totalRequests: this.metrics.totalRequests,
      recentTrends: {
        responseTimeImproving: this.isImproving(this.metrics.responseTime.map(r => r.time), false),
        accuracyImproving: this.isImproving(this.metrics.accuracy.map(a => a.accuracy), true),
        satisfactionImproving: this.isImproving(this.metrics.userSatisfaction.map(s => s.rating), true)
      }
    };
  }

  isImproving(values, higherIsBetter) {
    if (values.length < 10) return null;
    
    const recent = values.slice(-10);
    const older = values.slice(-20, -10);
    
    if (older.length === 0) return null;
    
    const recentAvg = recent.reduce((sum, v) => sum + v, 0) / recent.length;
    const olderAvg = older.reduce((sum, v) => sum + v, 0) / older.length;
    
    return higherIsBetter ? recentAvg > olderAvg : recentAvg < olderAvg;
  }

  shouldRetrain() {
    const report = this.getPerformanceReport();
    
    // Suggest retraining if:
    // - Average response time > 5 seconds
    // - Average accuracy < 70%
    // - User satisfaction < 3.5/5
    // - Performance is declining
    
    return (
      report.averageResponseTime > 5000 ||
      report.averageAccuracy < 70 ||
      report.averageUserSatisfaction < 3.5 ||
      (report.recentTrends.responseTimeImproving === false) ||
      (report.recentTrends.accuracyImproving === false) ||
      (report.recentTrends.satisfactionImproving === false)
    );
  }
}

module.exports = ModelPerformanceTracker;