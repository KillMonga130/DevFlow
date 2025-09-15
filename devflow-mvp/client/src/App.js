import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [currentView, setCurrentView] = useState('home');
  const [exercise, setExercise] = useState(null);
  const [selectedIssues, setSelectedIssues] = useState([]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({ totalAttempts: 0, averageScore: 0, bestScore: 0 });

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get('/api/stats');
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const generateExercise = async () => {
    setLoading(true);
    try {
      const response = await axios.post('/api/exercise/generate');
      setExercise(response.data);
      setSelectedIssues([]);
      setResults(null);
      setCurrentView('exercise');
    } catch (error) {
      console.error('Error generating exercise:', error);
      alert('Failed to generate exercise. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const toggleIssue = (lineNumber) => {
    const existingIssue = selectedIssues.find(issue => issue.line === lineNumber);
    
    if (existingIssue) {
      // Remove issue
      setSelectedIssues(selectedIssues.filter(issue => issue.line !== lineNumber));
    } else {
      // Add issue - for MVP, we'll use a simple modal or default type
      const issueType = prompt('What type of issue is this?\n\n1. security\n2. performance\n3. logic\n4. style\n\nEnter the type:') || 'logic';
      
      setSelectedIssues([...selectedIssues, {
        line: lineNumber,
        type: issueType.toLowerCase(),
        description: `Issue on line ${lineNumber}`
      }]);
    }
  };

  const submitReview = async () => {
    if (!exercise) return;
    
    setLoading(true);
    try {
      const response = await axios.post(`/api/exercise/${exercise.id}/submit`, {
        userIssues: selectedIssues
      });
      
      setResults(response.data);
      setCurrentView('results');
      fetchStats(); // Update stats
    } catch (error) {
      console.error('Error submitting review:', error);
      alert('Failed to submit review. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const startOver = () => {
    setCurrentView('home');
    setExercise(null);
    setSelectedIssues([]);
    setResults(null);
  };

  if (currentView === 'home') {
    return (
      <div className="app">
        <div className="container">
          <header className="header">
            <h1>🚀 DevFlow MVP</h1>
            <p>AI-Powered Code Review Education</p>
          </header>

          <div className="stats-card">
            <h3>Your Progress</h3>
            <div className="stats-grid">
              <div className="stat">
                <div className="stat-number">{stats.totalAttempts}</div>
                <div className="stat-label">Exercises</div>
              </div>
              <div className="stat">
                <div className="stat-number">{Math.round(stats.averageScore || 0)}%</div>
                <div className="stat-label">Avg Score</div>
              </div>
              <div className="stat">
                <div className="stat-number">{Math.round(stats.bestScore || 0)}%</div>
                <div className="stat-label">Best Score</div>
              </div>
            </div>
          </div>

          <div className="main-card">
            <h2>Ready to improve your code review skills?</h2>
            <p>Practice identifying bugs, security issues, and performance problems in real code.</p>
            
            <button 
              className="primary-button"
              onClick={generateExercise}
              disabled={loading}
            >
              {loading ? 'Generating...' : 'Start Code Review'}
            </button>
          </div>

          <div className="info-card">
            <h3>How it works:</h3>
            <ol>
              <li>Review the generated JavaScript code</li>
              <li>Click on lines where you find issues</li>
              <li>Specify the type of issue (security, performance, etc.)</li>
              <li>Submit your review and get instant feedback</li>
            </ol>
          </div>
        </div>
      </div>
    );
  }

  if (currentView === 'exercise') {
    return (
      <div className="app">
        <div className="container">
          <header className="header">
            <h1>🔍 Code Review Exercise</h1>
            <p>Find the issues in this JavaScript code</p>
          </header>

          <div className="exercise-card">
            <div className="code-container">
              <div className="code-header">
                <span>JavaScript Code</span>
                <span className="issues-count">
                  Issues found: {selectedIssues.length}
                </span>
              </div>
              
              <div className="code-content">
                {exercise?.code.split('\n').map((line, index) => {
                  const lineNumber = index + 1;
                  const hasIssue = selectedIssues.some(issue => issue.line === lineNumber);
                  
                  return (
                    <div 
                      key={lineNumber}
                      className={`code-line ${hasIssue ? 'has-issue' : ''}`}
                      onClick={() => toggleIssue(lineNumber)}
                    >
                      <span className="line-number">{lineNumber}</span>
                      <span className="line-content">{line}</span>
                      {hasIssue && <span className="issue-marker">⚠️</span>}
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="instructions">
              <h3>Instructions:</h3>
              <ul>
                <li>Click on any line where you think there's an issue</li>
                <li>You'll be asked to specify the type of issue</li>
                <li>Look for security vulnerabilities, performance problems, logic errors, and style issues</li>
                <li>When you're done, submit your review for feedback</li>
              </ul>
            </div>

            <div className="action-buttons">
              <button className="secondary-button" onClick={startOver}>
                Back to Home
              </button>
              <button 
                className="primary-button"
                onClick={submitReview}
                disabled={loading || selectedIssues.length === 0}
              >
                {loading ? 'Submitting...' : 'Submit Review'}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (currentView === 'results') {
    return (
      <div className="app">
        <div className="container">
          <header className="header">
            <h1>📊 Review Results</h1>
            <p>Here's how you did!</p>
          </header>

          <div className="results-card">
            <div className="score-section">
              <div className="score-circle">
                <div className="score-number">{results.score}%</div>
                <div className="score-label">Score</div>
              </div>
              
              <div className="feedback">
                <h3>{results.feedback.message}</h3>
                <p className="tip">{results.feedback.tip}</p>
              </div>
            </div>

            <div className="comparison-section">
              <div className="comparison-column">
                <h4>Issues You Found ({results.foundIssues.length})</h4>
                <div className="issues-list">
                  {results.foundIssues.map((issue, index) => (
                    <div key={index} className="issue-item found">
                      <span className="issue-line">Line {issue.line}</span>
                      <span className="issue-type">{issue.type}</span>
                    </div>
                  ))}
                  {results.foundIssues.length === 0 && (
                    <p className="no-issues">No issues identified</p>
                  )}
                </div>
              </div>

              <div className="comparison-column">
                <h4>Correct Issues ({results.correctIssues.length})</h4>
                <div className="issues-list">
                  {results.correctIssues.map((issue, index) => {
                    const wasFound = results.foundIssues.some(found => 
                      Math.abs(found.line - issue.line) <= 1 && found.type === issue.type
                    );
                    
                    return (
                      <div key={index} className={`issue-item ${wasFound ? 'correct' : 'missed'}`}>
                        <span className="issue-line">Line {issue.line}</span>
                        <span className="issue-type">{issue.type}</span>
                        <span className="issue-title">{issue.title}</span>
                        {!wasFound && <span className="missed-label">MISSED</span>}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="action-buttons">
              <button className="secondary-button" onClick={startOver}>
                Back to Home
              </button>
              <button className="primary-button" onClick={generateExercise}>
                Try Another Exercise
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
}

export default App;