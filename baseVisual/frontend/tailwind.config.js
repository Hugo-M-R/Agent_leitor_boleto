/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [require('daisyui')],
  daisyui: {
    themes: [
      {
        usercase: {
          primary: '#60a5fa',
          secondary: '#7dd3fc',
          accent: '#a5b4fc',
          neutral: '#0b0f17',
          'base-100': '#0b0f17',
          info: '#38bdf8',
          success: '#10b981',
          warning: '#f59e0b',
          error: '#ef4444',
        },
      },
      'dark',
    ],
    darkTheme: 'usercase',
  },
}


