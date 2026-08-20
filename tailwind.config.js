/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './apps/core/templates/**/*.html',
    './apps/poller/templates/**/*.html',
  ],
  theme: {
    extend: {
      screens: {
        xs: '360px',
      },
    },
  },
  plugins: [],
};
