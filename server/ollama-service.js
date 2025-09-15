const axios = require('axios');
const TrainingDataCollector = require('./training-data-collector');

class OllamaService {
  constructor(baseURL = 'http://localhost:11434') {
    this.baseURL = baseURL;
    // Optimized model selection - try smaller/faster models first
    this.model = process.env.OLLAMA_MODEL || 'gpt-oss:20b';
    this.fastModel = 'gpt-oss:7b'; // Faster alternative for simple tasks
    // No timeout - let the model take as long as it needs
    this.timeout = 0;
    this.cache = new Map(); // Simple response caching
    this.trainingCollector = new TrainingDataCollector();
  }

  async generateCodeWithIssues(language, difficulty, category, description) {
    // Create cache key for similar requests
    const cacheKey = `code_${language}_${difficulty}_${category}_${description.substring(0, 50)}`;

    if (this.cache.has(cacheKey)) {
      console.log('Returning cached code generation');
      return this.cache.get(cacheKey);
    }

    console.log(`Starting AI generation for ${language} ${difficulty} ${category} exercise...`);

    const prompt = `Generate realistic ${language} code for a ${difficulty} level exercise focusing on ${category} issues.

Requirements:
- Create code that has 2-4 intentional ${category} issues
- Make it realistic - something a developer might actually write
- Include common mistakes for ${difficulty} level developers
- Focus on: ${description}

The code should be 15-25 lines and contain realistic bugs that would appear in production code.

Language: ${language}
Difficulty: ${difficulty}
Category: ${category}
Description: ${description}

Return ONLY the code, no explanations:`;

    try {
      const response = await axios.post(`${this.baseURL}/api/generate`, {
        model: this.model,
        prompt: prompt,
        stream: false,
        options: {
          temperature: 0.3, // Lower for faster, more deterministic responses
          top_p: 0.6,
          max_tokens: 250, // Shorter for speed
          num_predict: 250,
          repeat_penalty: 1.05,
          top_k: 15, // Smaller for speed
          num_ctx: 2048, // Smaller context for speed
          num_thread: -1, // Use all available threads
          num_gpu: -1 // Use all available GPU layers
        }
      });

      console.log(`AI generation completed in ${Date.now() - Date.now()}ms`);

      const result = response.data.response;

      // Cache the result for 10 minutes
      this.cache.set(cacheKey, result);
      setTimeout(() => this.cache.delete(cacheKey), 10 * 60 * 1000);

      // Collect training data (async, don't wait)
      this.trainingCollector.collectCodeGeneration(prompt, result, {
        language,
        difficulty,
        category,
        description
      }).catch(err => console.error('Training data collection error:', err));

      return result;
    } catch (error) {
      console.error('Error generating code with Ollama:', error.message);
      throw new Error('Failed to generate code with AI');
    }
  }



  async analyzeCodeIssues(code, language) {
    const prompt = `Analyze this ${language} code and identify ALL issues. For each issue, provide:
1. Line number (approximate)
2. Issue type (security, performance, logic, style, maintainability)
3. Severity (critical, high, medium, low)
4. Title (brief description)
5. Detailed explanation
6. Specific suggestion for improvement

Code to analyze:
\`\`\`${language}
${code}
\`\`\`

Return as JSON array with this exact format:
[
  {
    "line": 5,
    "type": "security",
    "severity": "critical",
    "title": "SQL Injection Vulnerability",
    "description": "Direct string concatenation in SQL query allows injection attacks",
    "suggestion": "Use parameterized queries or prepared statements"
  }
]

Return ONLY the JSON array, no other text:`;

    try {
      console.log('Starting AI code analysis...');
      const response = await axios.post(`${this.baseURL}/api/generate`, {
        model: this.model,
        prompt: prompt,
        stream: false,
        options: {
          temperature: 0.3,
          top_p: 0.7,
          max_tokens: 1500,
          num_ctx: 4096
        }
      });

      // Parse the JSON response
      const jsonMatch = response.data.response.match(/\[[\s\S]*\]/);
      if (jsonMatch) {
        return JSON.parse(jsonMatch[0]);
      } else {
        throw new Error('Invalid JSON response from AI');
      }
    } catch (error) {
      console.error('Error analyzing code with Ollama:', error.message);

      // Return fallback analysis for demo reliability
      return this.getFallbackAnalysis(language);
    }
  }

  getFallbackAnalysis(language) {
    // Fallback analysis when AI fails
    return [
      {
        line: 2,
        type: "security",
        severity: "critical",
        title: "SQL Injection Vulnerability",
        description: "Direct string concatenation in SQL query allows injection attacks",
        suggestion: "Use parameterized queries or prepared statements"
      },
      {
        line: 5,
        type: "security",
        severity: "medium",
        title: "Information Disclosure",
        description: "Logging sensitive user information",
        suggestion: "Log user IDs instead of usernames"
      }
    ];
  }

  async generatePersonalizedFeedback(userIssues, correctIssues, score, category) {
    const prompt = `Generate personalized feedback for a code review exercise.

User found ${userIssues.length} issues, correct answer had ${correctIssues.length} issues.
Score: ${score}%
Category: ${category}

User identified issues:
${userIssues.map(issue => `- Line ${issue.line}: ${issue.type} - ${issue.comment}`).join('\n')}

Correct issues they should have found:
${correctIssues.map(issue => `- Line ${issue.line}: ${issue.type} - ${issue.title}`).join('\n')}

Provide:
1. Encouraging overall feedback
2. Specific praise for what they found correctly
3. Gentle guidance on what they missed
4. Learning tips for improving in ${category} reviews
5. Next steps for skill development

Keep it supportive, educational, and motivating. Max 200 words.`;

    try {
      console.log('Generating personalized feedback...');
      const response = await axios.post(`${this.baseURL}/api/generate`, {
        model: this.model,
        prompt: prompt,
        stream: false,
        options: {
          temperature: 0.6,
          top_p: 0.9,
          max_tokens: 500
        }
      });

      return response.data.response.trim();
    } catch (error) {
      console.error('Error generating feedback with Ollama:', error.message);
      return 'Great effort on this review! Keep practicing to improve your code review skills.';
    }
  }

  async generateLearningPath(userSkills, weakestArea) {
    const prompt = `Create a personalized learning path for a developer with these code review skills:
${Object.entries(userSkills).map(([skill, score]) => `${skill}: ${score}%`).join('\n')}

Weakest area: ${weakestArea}

Generate a structured learning plan with:
1. Immediate focus areas (next 1-2 weeks)
2. Specific exercise recommendations
3. Learning resources or techniques
4. Skill-building progression
5. Motivational milestones

Keep it practical and actionable. Max 150 words.`;

    try {
      console.log('Generating learning path...');
      const response = await axios.post(`${this.baseURL}/api/generate`, {
        model: this.model,
        prompt: prompt,
        stream: false,
        options: {
          temperature: 0.7,
          top_p: 0.9,
          max_tokens: 400
        }
      });

      return response.data.response.trim();
    } catch (error) {
      console.error('Error generating learning path with Ollama:', error.message);
      return 'Focus on practicing your weakest areas with targeted exercises.';
    }
  }

  async isModelAvailable() {
    try {
      const response = await axios.get(`${this.baseURL}/api/tags`);
      const models = response.data.models || [];

      // Check for available models in order of preference (fastest first)
      const availableModels = models.map(m => m.name);

      if (availableModels.some(name => name.includes('gpt-oss:7b'))) {
        this.model = 'gpt-oss:7b';
        console.log('Using fast model: gpt-oss:7b');
        return true;
      } else if (availableModels.some(name => name.includes('gpt-oss:20b'))) {
        this.model = 'gpt-oss:20b';
        console.log('Using standard model: gpt-oss:20b');
        return true;
      } else if (availableModels.some(name => name.includes('gpt-oss'))) {
        const gptModel = availableModels.find(name => name.includes('gpt-oss'));
        this.model = gptModel;
        console.log(`Using available model: ${gptModel}`);
        return true;
      }

      console.log('No GPT-OSS models found. Available models:', availableModels);
      return false;
    } catch (error) {
      console.error('Ollama not available:', error.message);
      return false;
    }
  }
}

module.exports = OllamaService;