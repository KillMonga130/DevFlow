const OllamaService = require('./server/ollama-service');

async function testOllama() {
  const ollama = new OllamaService();
  
  console.log('Testing Ollama connection...');
  
  try {
    const isAvailable = await ollama.isModelAvailable();
    console.log('Model available:', isAvailable);
    
    if (isAvailable) {
      console.log('\n✅ Ollama is working! Testing code generation...');
      
      const code = await ollama.generateCodeWithIssues(
        'javascript',
        'beginner',
        'security',
        'Basic authentication function with common security flaws'
      );
      
      console.log('\n🎯 Generated code:');
      console.log('---');
      console.log(code);
      console.log('---');
      
      console.log('\n🔍 Testing code analysis...');
      const analysis = await ollama.analyzeCodeIssues(code, 'javascript');
      console.log('Found', analysis.length, 'issues:');
      analysis.forEach((issue, i) => {
        console.log(`${i + 1}. Line ${issue.line}: ${issue.type} - ${issue.title}`);
      });
      
    } else {
      console.log('❌ Ollama model not available. Check your setup.');
    }
    
  } catch (error) {
    console.error('❌ Error testing Ollama:', error.message);
  }
}

testOllama();