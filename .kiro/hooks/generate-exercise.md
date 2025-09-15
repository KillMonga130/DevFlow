# Generate Code Review Exercise Hook

## Trigger
Manual execution via Kiro Hook UI

## Purpose
Automatically generate new code review exercises with intentional bugs and issues for different skill levels and programming languages.

## Input Parameters
- `language`: Programming language (javascript, python, typescript)
- `difficulty`: Skill level (beginner, intermediate, advanced)
- `category`: Issue type (security, performance, style, logic)

## Expected Output
- Generate flawed code snippet with 2-4 intentional issues
- Create JSON metadata describing each issue
- Save to database for use in training exercises

## Implementation Notes
- Use realistic code patterns that developers encounter
- Ensure issues are educational, not trivial
- Include both obvious and subtle problems
- Provide detailed explanations for learning purposes

## Example Usage
When a user completes all exercises in a category, this hook automatically generates new content to keep the learning experience fresh.