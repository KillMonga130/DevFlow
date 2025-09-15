# Update User Progress Hook

## Trigger
After user completes a code review exercise

## Purpose
Automatically update user skill progress and generate personalized recommendations based on performance patterns.

## Input Parameters
- `userId`: User identifier
- `exerciseId`: Completed exercise ID
- `score`: Review accuracy score (0-100)
- `category`: Exercise category (security, performance, logic, style)
- `timeSpent`: Time taken to complete review (seconds)

## Expected Output
- Update skill_progress table with new accuracy scores
- Generate achievement notifications if milestones reached
- Create personalized learning recommendations
- Update user streak and statistics

## Implementation Notes
- Calculate rolling average for accuracy scores
- Identify weak areas for targeted practice suggestions
- Track improvement trends over time
- Generate motivational achievements and badges

## Example Usage
When a user submits a review, this hook processes their performance data and updates their learning profile automatically.