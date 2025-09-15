# Content Refresh Hook

## Trigger
Daily at 2 AM UTC or manual execution

## Purpose
Automatically generate fresh code review exercises to keep the learning experience engaging and prevent users from memorizing solutions.

## Input Parameters
- `targetCount`: Number of new exercises to generate per category
- `languages`: Array of programming languages to focus on
- `difficultyDistribution`: Percentage split for beginner/intermediate/advanced

## Expected Output
- Generate new flawed code examples with realistic bugs
- Create comprehensive issue metadata with explanations
- Ensure variety in problem types and complexity
- Archive old exercises that have been completed many times

## Implementation Notes
- Use AI to generate code with intentional issues
- Validate that generated issues are educational and realistic
- Maintain balance across different skill categories
- Include trending security vulnerabilities and performance patterns

## Example Usage
Runs automatically to ensure users always have fresh content, or can be triggered manually when launching new learning modules.