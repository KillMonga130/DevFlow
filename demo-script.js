#!/usr/bin/env node

const readline = require('readline');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

console.log('🎬 DevFlow Demo Script - Code with Kiro Hackathon');
console.log('='.repeat(60));
console.log('');

const demoSteps = [
  {
    title: '🎯 Project Overview',
    content: `DevFlow is a code review training platform that teaches developers to identify:
    • Security vulnerabilities (SQL injection, XSS, etc.)
    • Performance bottlenecks (O(n²) algorithms, memory leaks)
    • Logic errors (resource leaks, edge cases)
    • Code style issues (maintainability, readability)
    
    Built entirely using Kiro's AI-assisted development workflow!`
  },
  {
    title: '📋 Kiro Spec-Driven Development',
    content: `Check out .kiro/specs/codebuddy-core.md:
    • Detailed feature specifications with user stories
    • Technical architecture decisions
    • Database schema design
    • Implementation phases
    
    Kiro helped structure the entire project from this spec!`
  },
  {
    title: '🤖 Agent Hooks for Automation',
    content: `Three powerful hooks in .kiro/hooks/:
    
    1. generate-exercise.md - Auto-creates new review exercises
    2. update-progress.md - Tracks user skill development  
    3. content-refresh.md - Keeps content fresh and engaging
    
    These hooks automate the most time-consuming parts of content management!`
  },
  {
    title: '🎨 AI-Assisted Full-Stack Development',
    content: `Kiro helped build:
    • React + TypeScript frontend with Monaco Editor
    • Node.js/Express backend with SQLite
    • Interactive code review interface
    • Progress tracking and analytics
    • Responsive design with Tailwind CSS
    
    From conversation to production-ready code!`
  },
  {
    title: '💡 Unique Value Proposition',
    content: `Why DevFlow stands out:
    • Learns by REVIEWING code, not writing it
    • Realistic flawed code examples from real-world scenarios
    • Progressive skill building across multiple categories
    • Immediate feedback with expert explanations
    • Gamified learning with achievements and progress tracking
    
    Addresses the critical skill gap in code review!`
  },
  {
    title: '🏆 Hackathon Categories',
    content: `Perfect fit for "Educational Apps" category:
    • Solves real developer education problem
    • Innovative approach to learning code review
    • Showcases ALL Kiro features meaningfully
    • Production-ready with polished UX
    • Scalable architecture for growth
    
    Could also compete in "Wildcard" for unique approach!`
  },
  {
    title: '🚀 Live Demo Flow',
    content: `Demo sequence:
    1. Show exercise list with filtering
    2. Select a security-focused JavaScript exercise
    3. Walk through the interactive review process
    4. Identify issues using the annotation system
    5. Submit review and show detailed feedback
    6. Display progress dashboard with skill tracking
    
    Emphasize the realistic code and educational value!`
  },
  {
    title: '📊 Impact & Scalability',
    content: `DevFlow addresses:
    • Critical skill gap in software engineering
    • Expensive onboarding for junior developers
    • Inconsistent code review practices across teams
    • Lack of structured learning for code review skills
    
    Potential to transform how developers learn this essential skill!`
  }
];

function showStep(index) {
  if (index >= demoSteps.length) {
    console.log('🎉 Demo script complete! Ready to showcase DevFlow!');
    console.log('');
    console.log('Quick start commands:');
    console.log('  npm run setup    # First time setup');
    console.log('  npm run dev      # Start development servers');
    console.log('  npm run demo     # Run this demo script again');
    console.log('');
    rl.close();
    return;
  }

  const step = demoSteps[index];
  console.log(`${step.title}`);
  console.log('-'.repeat(40));
  console.log(step.content);
  console.log('');
  
  rl.question('Press Enter to continue (or "q" to quit): ', (answer) => {
    if (answer.toLowerCase() === 'q') {
      console.log('Demo ended. Good luck with your presentation! 🚀');
      rl.close();
      return;
    }
    console.log('');
    showStep(index + 1);
  });
}

// Start the demo
showStep(0);