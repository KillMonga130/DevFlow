import React, { useState, useEffect, useRef } from 'react';
import { AlertTriangle, CheckCircle, Clock, Lightbulb, Zap } from 'lucide-react';

const LiveCodeReview = ({ code, language, onIssueFound, onComplete }) => {
  const [foundIssues, setFoundIssues] = useState([]);
  const [selectedLine, setSelectedLine] = useState(null);
  const [comment, setComment] = useState('');
  const [issueType, setIssueType] = useState('security');
  const [severity, setSeverity] = useState('medium');
  const [timeSpent, setTimeSpent] = useState(0);
  const [hints, setHints] = useState([]);
  const [showHint, setShowHint] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  
  const startTime = useRef(Date.now());
  const timerRef = useRef(null);

  useEffect(() => {
    // Start timer
    timerRef.current = setInterval(() => {
      setTimeSpent(Math.floor((Date.now() - startTime.current) / 1000));
    }, 1000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  useEffect(() => {
    // Get AI analysis for comparison (hidden from user initially)
    getAIAnalysis();
  }, [code, language]);

  const getAIAnalysis = async () => {
    setIsAnalyzing(true);
    try {
      const response = await fetch('/api/analyze-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, language })
      });
      const analysis = await response.json();
      setAiAnalysis(analysis);
      
      // Generate contextual hints
      generateHints(analysis);
    } catch (error) {
      console.error('Error getting AI analysis:', error);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const generateHints = (analysis) => {
    const hintMessages = [
      "Look for potential security vulnerabilities in user input handling",
      "Check for performance issues like inefficient loops or database queries",
      "Examine error handling and edge cases",
      "Review variable naming and code structure",
      "Consider memory leaks or resource management issues"
    ];

    // Generate hints based on actual issues found by AI
    const contextualHints = analysis.map(issue => {
      switch (issue.type) {
        case 'security':
          return `Security tip: Look around line ${issue.line} for input validation issues`;
        case 'performance':
          return `Performance tip: Check line ${issue.line} for optimization opportunities`;
        case 'logic':
          return `Logic tip: Review the flow around line ${issue.line}`;
        default:
          return `Code quality: Examine line ${issue.line} for best practices`;
      }
    });

    setHints([...hintMessages.slice(0, 2), ...contextualHints.slice(0, 2)]);
  };

  const handleLineClick = (lineNumber) => {
    setSelectedLine(lineNumber);
    setComment('');
  };

  const addIssue = () => {
    if (!selectedLine || !comment.trim()) return;

    const newIssue = {
      line: selectedLine,
      type: issueType,
      severity,
      comment: comment.trim(),
      timestamp: Date.now()
    };

    setFoundIssues([...foundIssues, newIssue]);
    onIssueFound(newIssue);
    
    // Clear form
    setSelectedLine(null);
    setComment('');
    
    // Provide immediate feedback
    checkIssueAccuracy(newIssue);
  };

  const checkIssueAccuracy = (userIssue) => {
    if (!aiAnalysis) return;

    // Check if user found a real issue
    const matchingIssue = aiAnalysis.find(issue => 
      Math.abs(issue.line - userIssue.line) <= 2 && 
      issue.type === userIssue.type
    );

    if (matchingIssue) {
      // Show positive feedback
      showFeedback('Great catch! You found a real issue.', 'success');
    }
  };

  const showFeedback = (message, type) => {
    // This would trigger a toast notification
    console.log(`${type}: ${message}`);
  };

  const completeReview = async () => {
    const reviewData = {
      foundIssues,
      timeSpent,
      code,
      language,
      aiAnalysis
    };

    try {
      const response = await fetch('/api/submit-review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reviewData)
      });
      
      const result = await response.json();
      onComplete(result);
    } catch (error) {
      console.error('Error submitting review:', error);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getIssueIcon = (type) => {
    switch (type) {
      case 'security': return <AlertTriangle className="w-4 h-4 text-red-500" />;
      case 'performance': return <Zap className="w-4 h-4 text-yellow-500" />;
      default: return <CheckCircle className="w-4 h-4 text-blue-500" />;
    }
  };

  return (
    <div className="flex flex-col lg:flex-row gap-6 h-full">
      {/* Code Display */}
      <div className="flex-1 bg-gray-900 rounded-lg overflow-hidden">
        <div className="bg-gray-800 px-4 py-2 flex items-center justify-between">
          <span className="text-gray-300 text-sm font-medium">{language}</span>
          <div className="flex items-center space-x-4 text-gray-300 text-sm">
            <div className="flex items-center space-x-1">
              <Clock className="w-4 h-4" />
              <span>{formatTime(timeSpent)}</span>
            </div>
            <div className="flex items-center space-x-1">
              <CheckCircle className="w-4 h-4" />
              <span>{foundIssues.length} issues found</span>
            </div>
          </div>
        </div>
        
        <div className="p-4 overflow-auto max-h-96">
          <pre className="text-gray-100 text-sm leading-relaxed">
            {code.split('\n').map((line, index) => {
              const lineNumber = index + 1;
              const hasIssue = foundIssues.some(issue => issue.line === lineNumber);
              const isSelected = selectedLine === lineNumber;
              
              return (
                <div
                  key={lineNumber}
                  className={`flex hover:bg-gray-800 cursor-pointer transition-colors ${
                    isSelected ? 'bg-blue-900' : hasIssue ? 'bg-red-900/30' : ''
                  }`}
                  onClick={() => handleLineClick(lineNumber)}
                >
                  <span className="text-gray-500 w-8 text-right mr-4 select-none">
                    {lineNumber}
                  </span>
                  <span className="flex-1">{line}</span>
                  {hasIssue && (
                    <AlertTriangle className="w-4 h-4 text-red-400 ml-2 mt-0.5" />
                  )}
                </div>
              );
            })}
          </pre>
        </div>
      </div>

      {/* Review Panel */}
      <div className="w-full lg:w-80 space-y-4">
        {/* Add Issue Form */}
        {selectedLine && (
          <div className="bg-white rounded-lg shadow-md p-4">
            <h3 className="font-semibold text-gray-800 mb-3">
              Add Issue - Line {selectedLine}
            </h3>
            
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Issue Type
                </label>
                <select
                  value={issueType}
                  onChange={(e) => setIssueType(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                >
                  <option value="security">Security</option>
                  <option value="performance">Performance</option>
                  <option value="logic">Logic</option>
                  <option value="style">Style</option>
                  <option value="maintainability">Maintainability</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Severity
                </label>
                <select
                  value={severity}
                  onChange={(e) => setSeverity(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                >
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="Describe the issue and suggest improvements..."
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm h-20 resize-none"
                />
              </div>

              <button
                onClick={addIssue}
                disabled={!comment.trim()}
                className="w-full bg-blue-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Add Issue
              </button>
            </div>
          </div>
        )}

        {/* Found Issues */}
        <div className="bg-white rounded-lg shadow-md p-4">
          <h3 className="font-semibold text-gray-800 mb-3">Issues Found</h3>
          
          {foundIssues.length === 0 ? (
            <p className="text-gray-500 text-sm">No issues found yet. Click on a line to add one.</p>
          ) : (
            <div className="space-y-2">
              {foundIssues.map((issue, index) => (
                <div key={index} className="border border-gray-200 rounded-md p-3">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center space-x-2">
                      {getIssueIcon(issue.type)}
                      <span className="text-sm font-medium">Line {issue.line}</span>
                    </div>
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      issue.severity === 'critical' ? 'bg-red-100 text-red-800' :
                      issue.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                      issue.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {issue.severity}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600">{issue.comment}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Hints */}
        <div className="bg-white rounded-lg shadow-md p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-gray-800">Hints</h3>
            <button
              onClick={() => setShowHint(!showHint)}
              className="text-blue-600 hover:text-blue-700 text-sm font-medium"
            >
              {showHint ? 'Hide' : 'Show'} Hint
            </button>
          </div>
          
          {showHint && hints.length > 0 && (
            <div className="bg-blue-50 rounded-md p-3">
              <div className="flex items-start space-x-2">
                <Lightbulb className="w-4 h-4 text-blue-500 mt-0.5" />
                <p className="text-sm text-blue-700">{hints[0]}</p>
              </div>
            </div>
          )}
        </div>

        {/* Complete Review */}
        <button
          onClick={completeReview}
          className="w-full bg-green-600 text-white py-3 px-4 rounded-md font-medium hover:bg-green-700 transition-colors"
        >
          Complete Review
        </button>
      </div>
    </div>
  );
};

export default LiveCodeReview;