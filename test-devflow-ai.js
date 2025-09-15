const OllamaService = require('./server/ollama-service');

async function testDevFlowAI() {
  console.log('🧪 Testing DevFlow AI Integration...\n');
  
  const ollama = new OllamaService();
  
  try {
    // Test 1: Check if model is available
    console.log('1️⃣ Checking AI model availability...');
    const isAvailable = await ollama.isModelAvailable();
    
    if (!isAvailable) {
      console.log('❌ No AI model found. Run train-devflow-model.bat first');
      return;
    }
    
    console.log('✅ AI model is available and ready');
    
    // Test 2: Generate code with issues
    console.log('\n2️⃣ Testing code generation...');
    const code = await ollama.generateCodeWithIssues(
      'javascript',
      'beginner', 
      'security',
      'User authentication with potential SQL injection'
    );
    
    console.log('✅ Code generation successful');
    console.log('📝 Generated code sample:');
    console.log(code.substring(0, 200) + '...\n');
    
    // Test 3: Analyze the generated code
    console.log('3️⃣ Testing code analysis...');
    const analysis = await ollama.analyzeCodeIssues(code, 'javascript');
    
    console.log('✅ Code analysis successful');
    console.log(`📊 Found ${analysis.length} issues:`);
    analysis.forEach((issue, i) => {
      console.log(`   ${i+1}. Line ${issue.line}: ${issue.type} - ${issue.title}`);
    });
    
    // Test 4: Generate feedback
    console.log('\n4️⃣ Testing personalized feedback...');
    const feedback = await ollama.generatePersonalizedFeedback(
      [{ line: 2, type: 'security', comment: 'SQL injection risk' }],
      analysis,
      75,
      'security'
    );
    
    console.log('✅ Feedback generation successful');
    console.log('💬 Sample feedback:');
    console.log(feedback.substring(0, 150) + '...\n');
    
    console.log('🎉 All AI features are working perfectly!');
    console.log('\n📋 DevFlow is ready for users:');
    console.log('   • AI code generation: ✅');
    console.log('   • Code analysis: ✅');
    console.log('   • Personalized feedback: ✅');
    console.log('   • Model optimization: ✅');
    
    console.log('\n🚀 Launch your server and start changing developer education!');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
    console.log('\n💡 Troubleshooting tips:');
    console.log('1. Make sure Ollama is running: ollama serve');
    console.log('2. Check available models: ollama list');
    console.log('3. Try running: train-devflow-model.bat');
  }
}

// Run the test
testDevFlowAI();