const fs = require('fs').promises;
const path = require('path');

class TrainingDataCollector {
  constructor() {
    this.dataDir = path.join(__dirname, 'training-data');
    this.ensureDataDir();
  }

  async ensureDataDir() {
    try {
      await fs.mkdir(this.dataDir, { recursive: true });
      await fs.mkdir(path.join(this.dataDir, 'code-generation'), { recursive: true });
      await fs.mkdir(path.join(this.dataDir, 'code-analysis'), { recursive: true });
      await fs.mkdir(path.join(this.dataDir, 'feedback'), { recursive: true });
    } catch (error) {
      console.error('Error creating training data directories:', error);
    }
  }

  // Collect successful code generation examples
  async collectCodeGeneration(prompt, response, metadata) {
    const example = {
      timestamp: new Date().toISOString(),
      prompt,
      response,
      metadata: {
        language: metadata.language,
        difficulty: metadata.difficulty,
        category: metadata.category,
        userRating: metadata.userRating || null,
        exerciseCompleted: metadata.exerciseCompleted || false
      }
    };

    const filename = `code-gen-${Date.now()}.json`;
    await fs.writeFile(
      path.join(this.dataDir, 'code-generation', filename),
      JSON.stringify(example, null, 2)
    );
  }

  // Collect code analysis examples
  async collectCodeAnalysis(code, analysis, metadata) {
    const example = {
      timestamp: new Date().toISOString(),
      code,
      analysis,
      metadata: {
        language: metadata.language,
        userFoundIssues: metadata.userFoundIssues || [],
        accuracy: metadata.accuracy || null,
        timeSpent: metadata.timeSpent || null
      }
    };

    const filename = `analysis-${Date.now()}.json`;
    await fs.writeFile(
      path.join(this.dataDir, 'code-analysis', filename),
      JSON.stringify(example, null, 2)
    );
  }

  // Collect feedback examples
  async collectFeedback(userPerformance, feedback, metadata) {
    const example = {
      timestamp: new Date().toISOString(),
      userPerformance,
      feedback,
      metadata: {
        userLevel: metadata.userLevel,
        category: metadata.category,
        helpfulness: metadata.helpfulness || null
      }
    };

    const filename = `feedback-${Date.now()}.json`;
    await fs.writeFile(
      path.join(this.dataDir, 'feedback', filename),
      JSON.stringify(example, null, 2)
    );
  }

  // Generate training dataset for fine-tuning
  async generateTrainingDataset() {
    const datasets = {
      codeGeneration: await this.loadTrainingData('code-generation'),
      codeAnalysis: await this.loadTrainingData('code-analysis'),
      feedback: await this.loadTrainingData('feedback')
    };

    // Convert to fine-tuning format (JSONL)
    const trainingData = [];

    // Code generation examples
    for (const example of datasets.codeGeneration) {
      if (example.metadata.userRating >= 4) { // Only use highly rated examples
        trainingData.push({
          messages: [
            { role: "system", content: "You are a code review education assistant that generates realistic code with intentional issues for learning purposes." },
            { role: "user", content: example.prompt },
            { role: "assistant", content: example.response }
          ]
        });
      }
    }

    // Code analysis examples
    for (const example of datasets.codeAnalysis) {
      if (example.metadata.accuracy >= 0.8) { // Only use accurate analyses
        trainingData.push({
          messages: [
            { role: "system", content: "You are a code review expert that identifies issues in code and provides detailed analysis." },
            { role: "user", content: `Analyze this ${example.metadata.language} code:\n${example.code}` },
            { role: "assistant", content: JSON.stringify(example.analysis) }
          ]
        });
      }
    }

    // Save training dataset
    const jsonlData = trainingData.map(item => JSON.stringify(item)).join('\n');
    await fs.writeFile(
      path.join(this.dataDir, 'devflow-training-dataset.jsonl'),
      jsonlData
    );

    console.log(`Generated training dataset with ${trainingData.length} examples`);
    return path.join(this.dataDir, 'devflow-training-dataset.jsonl');
  }

  async loadTrainingData(category) {
    try {
      const files = await fs.readdir(path.join(this.dataDir, category));
      const data = [];

      for (const file of files) {
        if (file.endsWith('.json')) {
          const content = await fs.readFile(path.join(this.dataDir, category, file), 'utf8');
          data.push(JSON.parse(content));
        }
      }

      return data;
    } catch (error) {
      console.error(`Error loading training data for ${category}:`, error);
      return [];
    }
  }
}

module.exports = TrainingDataCollector;