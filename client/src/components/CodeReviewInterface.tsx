import React, { useState, useRef, useEffect } from 'react';
import Editor from '@monaco-editor/react';

interface Issue {
    line: number;
    type: string;
    severity: string;
    title: string;
    description: string;
    suggestion: string;
}

interface Exercise {
    id: number;
    language: string;
    difficulty: string;
    category: string;
    title: string;
    description: string;
    code_content: string;
    issues: Issue[];
}

interface UserIssue {
    line: number;
    type: string;
    comment: string;
    severity: string;
}

interface CodeReviewInterfaceProps {
    exercise: Exercise;
    onBack: () => void;
}

const CodeReviewInterface: React.FC<CodeReviewInterfaceProps> = ({ exercise, onBack }) => {
    const [userIssues, setUserIssues] = useState<UserIssue[]>([]);
    const [selectedLine, setSelectedLine] = useState<number | null>(null);
    const [reviewComment, setReviewComment] = useState('');
    const [issueType, setIssueType] = useState('logic');
    const [issueSeverity, setIssueSeverity] = useState('medium');
    const [showResults, setShowResults] = useState(false);
    const [results, setResults] = useState<any>(null);
    const [timeSpent, setTimeSpent] = useState(0);
    const [isReviewing, setIsReviewing] = useState(false);
    const editorRef = useRef<any>(null);
    const startTimeRef = useRef<number>(Date.now());

    useEffect(() => {
        const timer = setInterval(() => {
            setTimeSpent(Math.floor((Date.now() - startTimeRef.current) / 1000));
        }, 1000);

        return () => clearInterval(timer);
    }, []);

    const handleEditorDidMount = (editor: any) => {
        editorRef.current = editor;

        // Add click handler for line selection
        editor.onMouseDown((e: any) => {
            const position = e.target.position;
            if (position) {
                setSelectedLine(position.lineNumber);
            }
        });

        // Add decorations for user-identified issues
        updateDecorations();
    };

    const updateDecorations = () => {
        if (!editorRef.current) return;

        const decorations = userIssues.map(issue => ({
            range: {
                startLineNumber: issue.line,
                startColumn: 1,
                endLineNumber: issue.line,
                endColumn: 1000
            },
            options: {
                isWholeLine: true,
                className: `review-issue-${issue.severity}`,
                glyphMarginClassName: 'review-glyph',
                hoverMessage: { value: `**${issue.type.toUpperCase()}**: ${issue.comment}` }
            }
        }));

        editorRef.current.deltaDecorations([], decorations);
    };

    useEffect(() => {
        updateDecorations();
    }, [userIssues]);

    const addIssue = () => {
        if (!selectedLine || !reviewComment.trim()) return;

        const newIssue: UserIssue = {
            line: selectedLine,
            type: issueType,
            comment: reviewComment.trim(),
            severity: issueSeverity
        };

        setUserIssues([...userIssues, newIssue]);
        setReviewComment('');
        setSelectedLine(null);
    };

    const removeIssue = (index: number) => {
        setUserIssues(userIssues.filter((_, i) => i !== index));
    };

    const submitReview = async () => {
        setIsReviewing(true);

        try {
            const response = await fetch(`/api/exercises/${exercise.id}/submit`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    userId: 1, // Mock user ID
                    issuesFound: userIssues,
                    reviewComments: userIssues.map(i => i.comment).join('\n'),
                    timeSpent
                })
            });

            const data = await response.json();
            setResults(data);
            setShowResults(true);
        } catch (error) {
            console.error('Error submitting review:', error);
        } finally {
            setIsReviewing(false);
        }
    };

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case 'critical': return 'text-red-600 bg-red-50 border-red-200';
            case 'high': return 'text-orange-600 bg-orange-50 border-orange-200';
            case 'medium': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
            case 'low': return 'text-blue-600 bg-blue-50 border-blue-200';
            default: return 'text-gray-600 bg-gray-50 border-gray-200';
        }
    };

    if (showResults && results) {
        return (
            <div className="space-y-6">
                <div className="bg-white p-6 rounded-lg shadow-md">
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-2xl font-bold text-gray-800">Review Results</h2>
                        <button
                            onClick={onBack}
                            className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
                        >
                            Back to Exercises
                        </button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                        <div className="text-center p-4 bg-blue-50 rounded-lg">
                            <div className="text-3xl font-bold text-blue-600">{results.score}%</div>
                            <div className="text-sm text-gray-600">Overall Score</div>
                        </div>
                        <div className="text-center p-4 bg-green-50 rounded-lg">
                            <div className="text-3xl font-bold text-green-600">{results.foundIssues.length}</div>
                            <div className="text-sm text-gray-600">Issues Found</div>
                        </div>
                        <div className="text-center p-4 bg-purple-50 rounded-lg">
                            <div className="text-3xl font-bold text-purple-600">{formatTime(timeSpent)}</div>
                            <div className="text-sm text-gray-600">Time Spent</div>
                        </div>
                    </div>

                    <div className="mb-6">
                        <h3 className="text-lg font-semibold mb-2">Feedback</h3>
                        <p className="text-gray-700 bg-gray-50 p-4 rounded-lg">{results.feedback.overall}</p>
                        
                        {results.feedback.ai_feedback && (
                            <div className="mt-4 p-4 bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg">
                                <div className="flex items-center mb-2">
                                    <span className="text-lg mr-2">🤖</span>
                                    <h4 className="font-medium text-blue-800">AI-Powered Personalized Feedback</h4>
                                </div>
                                <p className="text-blue-700 text-sm">{results.feedback.ai_feedback}</p>
                            </div>
                        )}
                    </div>

                    {results.feedback.missed.length > 0 && (
                        <div className="mb-6">
                            <h3 className="text-lg font-semibold mb-3 text-red-600">Missed Issues</h3>
                            <div className="space-y-3">
                                {results.feedback.missed.map((issue: Issue, index: number) => (
                                    <div key={index} className="border border-red-200 bg-red-50 p-4 rounded-lg">
                                        <div className="flex justify-between items-start mb-2">
                                            <h4 className="font-medium text-red-800">{issue.title}</h4>
                                            <span className="text-xs px-2 py-1 bg-red-200 text-red-800 rounded-full">
                                                Line {issue.line}
                                            </span>
                                        </div>
                                        <p className="text-red-700 text-sm mb-2">{issue.description}</p>
                                        <p className="text-red-600 text-sm font-medium">💡 {issue.suggestion}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    <div className="mb-6">
                        <h3 className="text-lg font-semibold mb-3 text-green-600">Correctly Identified</h3>
                        <div className="space-y-3">
                            {results.foundIssues.map((issue: UserIssue, index: number) => (
                                <div key={index} className="border border-green-200 bg-green-50 p-4 rounded-lg">
                                    <div className="flex justify-between items-start mb-2">
                                        <h4 className="font-medium text-green-800">{issue.type.toUpperCase()}</h4>
                                        <span className="text-xs px-2 py-1 bg-green-200 text-green-800 rounded-full">
                                            Line {issue.line}
                                        </span>
                                    </div>
                                    <p className="text-green-700 text-sm">{issue.comment}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="bg-white p-6 rounded-lg shadow-md">
                <div className="flex justify-between items-center mb-4">
                    <div>
                        <h2 className="text-2xl font-bold text-gray-800">{exercise.title}</h2>
                        <p className="text-gray-600">{exercise.description}</p>
                    </div>
                    <div className="flex items-center space-x-4">
                        <div className="text-right">
                            <div className="text-sm text-gray-500">Time Spent</div>
                            <div className="text-lg font-mono font-bold">{formatTime(timeSpent)}</div>
                        </div>
                        <button
                            onClick={onBack}
                            className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
                        >
                            Back
                        </button>
                    </div>
                </div>

                <div className="flex space-x-2">
                    <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                        {exercise.language}
                    </span>
                    <span className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm font-medium">
                        {exercise.difficulty}
                    </span>
                    <span className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm font-medium">
                        {exercise.category}
                    </span>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Code Editor */}
                <div className="lg:col-span-2">
                    <div className="bg-white rounded-lg shadow-md overflow-hidden">
                        <div className="bg-gray-50 px-4 py-2 border-b">
                            <h3 className="font-medium text-gray-800">Code to Review</h3>
                            {selectedLine && (
                                <p className="text-sm text-blue-600">Selected line: {selectedLine}</p>
                            )}
                        </div>
                        <div className="h-96">
                            <Editor
                                height="100%"
                                language={exercise.language}
                                value={exercise.code_content}
                                onMount={handleEditorDidMount}
                                options={{
                                    readOnly: true,
                                    minimap: { enabled: false },
                                    lineNumbers: 'on',
                                    glyphMargin: true,
                                    folding: false,
                                    lineDecorationsWidth: 10,
                                    lineNumbersMinChars: 3
                                }}
                                theme="vs-light"
                            />
                        </div>
                    </div>
                </div>

                {/* Review Panel */}
                <div className="space-y-4">
                    {/* Add Issue Form */}
                    <div className="bg-white p-4 rounded-lg shadow-md">
                        <h3 className="font-medium text-gray-800 mb-3">Add Issue</h3>

                        <div className="space-y-3">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Line Number
                                </label>
                                <input
                                    type="number"
                                    value={selectedLine || ''}
                                    onChange={(e) => setSelectedLine(parseInt(e.target.value) || null)}
                                    className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    placeholder="Click on code or enter line number"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Issue Type
                                </label>
                                <select
                                    value={issueType}
                                    onChange={(e) => setIssueType(e.target.value)}
                                    className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                >
                                    <option value="security">Security</option>
                                    <option value="performance">Performance</option>
                                    <option value="logic">Logic Error</option>
                                    <option value="style">Code Style</option>
                                    <option value="maintainability">Maintainability</option>
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Severity
                                </label>
                                <select
                                    value={issueSeverity}
                                    onChange={(e) => setIssueSeverity(e.target.value)}
                                    className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                >
                                    <option value="critical">Critical</option>
                                    <option value="high">High</option>
                                    <option value="medium">Medium</option>
                                    <option value="low">Low</option>
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Comment
                                </label>
                                <textarea
                                    value={reviewComment}
                                    onChange={(e) => setReviewComment(e.target.value)}
                                    className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    rows={3}
                                    placeholder="Describe the issue and suggest improvements..."
                                />
                            </div>

                            <button
                                onClick={addIssue}
                                disabled={!selectedLine || !reviewComment.trim()}
                                className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                            >
                                Add Issue
                            </button>
                        </div>
                    </div>

                    {/* Issues List */}
                    <div className="bg-white p-4 rounded-lg shadow-md">
                        <h3 className="font-medium text-gray-800 mb-3">
                            Issues Found ({userIssues.length})
                        </h3>

                        <div className="space-y-2 max-h-64 overflow-y-auto">
                            {userIssues.map((issue, index) => (
                                <div key={index} className={`p-3 rounded-lg border ${getSeverityColor(issue.severity)}`}>
                                    <div className="flex justify-between items-start mb-1">
                                        <span className="font-medium text-sm">Line {issue.line}</span>
                                        <button
                                            onClick={() => removeIssue(index)}
                                            className="text-red-500 hover:text-red-700 text-sm"
                                        >
                                            ✕
                                        </button>
                                    </div>
                                    <div className="text-xs font-medium mb-1">{issue.type.toUpperCase()}</div>
                                    <div className="text-sm">{issue.comment}</div>
                                </div>
                            ))}
                        </div>

                        {userIssues.length === 0 && (
                            <p className="text-gray-500 text-sm text-center py-4">
                                No issues identified yet. Click on code lines to start reviewing.
                            </p>
                        )}
                    </div>

                    {/* Submit Button */}
                    <button
                        onClick={submitReview}
                        disabled={userIssues.length === 0 || isReviewing}
                        className="w-full px-6 py-3 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
                    >
                        {isReviewing ? 'Submitting...' : 'Submit Review'}
                    </button>
                </div>
            </div>


        </div>
    );
};

export default CodeReviewInterface;