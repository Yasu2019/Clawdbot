const defaultTheme = require('tailwindcss/defaultTheme')

//Tailwind CSS 縦書き対応 :writing-mode
//https://tech-lab.sios.jp/archives/31882#:~:text=Tailwind%20CSS%20%E7%B8%A6%E6%9B%B8%E3%81%8D%E5%AF%BE%E5%BF%9C%20%3Awriting-mode%201%20%E4%BA%8B%E5%89%8D%E6%BA%96%E5%82%99%20Tailwind%20CSS%E3%81%AE%E7%92%B0%E5%A2%83%E6%A7%8B%E7%AF%89%E3%81%AF%E3%80%81,...%203%20Plugin%E3%81%A7%E8%A9%A6%E3%81%99%E7%B8%A6%E6%9B%B8%E3%81%8D%E5%AF%BE%E5%BF%9C%20%E3%81%93%E3%81%A1%E3%82%89%E3%81%AF%E3%80%81%E3%80%8Ctailwind.config.js%E3%80%8D%E3%81%AB%E8%BF%BD%E8%A8%98%E3%81%99%E3%82%8B%E3%81%93%E3%81%A8%E3%81%A7%E5%AE%9F%E7%8F%BE%E3%81%99%E3%82%8B%E3%81%93%E3%81%A8%E3%81%8C%E3%81%A7%E3%81%8D%E3%81%BE%E3%81%99%E3%80%82%20...%204%20%E7%B5%82%E3%82%8F%E3%82%8A%E3%81%AB%20
const plugin = require("tailwindcss/plugin");

//'./app/views/**/*.html.erb',　これで成功したことある


module.exports = {

  
  content: [
    './app/views/**/*.html.erb',
  ],


  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter var', ...defaultTheme.fontFamily.sans],
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/aspect-ratio'),
    require('@tailwindcss/typography'),
    require('daisyui'),    // ← 追加
    //【Tailwind CSS】長い文字列を三点リーダー（…）で省略する方法
    // https://zenn.dev/ilove/articles/8a93705d396e05
    



    //Tailwind CSS 縦書き対応 :writing-mode
    //https://tech-lab.sios.jp/archives/31882#:~:text=Tailwind%20CSS%20%E7%B8%A6%E6%9B%B8%E3%81%8D%E5%AF%BE%E5%BF%9C%20%3Awriting-mode%201%20%E4%BA%8B%E5%89%8D%E6%BA%96%E5%82%99%20Tailwind%20CSS%E3%81%AE%E7%92%B0%E5%A2%83%E6%A7%8B%E7%AF%89%E3%81%AF%E3%80%81,...%203%20Plugin%E3%81%A7%E8%A9%A6%E3%81%99%E7%B8%A6%E6%9B%B8%E3%81%8D%E5%AF%BE%E5%BF%9C%20%E3%81%93%E3%81%A1%E3%82%89%E3%81%AF%E3%80%81%E3%80%8Ctailwind.config.js%E3%80%8D%E3%81%AB%E8%BF%BD%E8%A8%98%E3%81%99%E3%82%8B%E3%81%93%E3%81%A8%E3%81%A7%E5%AE%9F%E7%8F%BE%E3%81%99%E3%82%8B%E3%81%93%E3%81%A8%E3%81%8C%E3%81%A7%E3%81%8D%E3%81%BE%E3%81%99%E3%80%82%20...%204%20%E7%B5%82%E3%82%8F%E3%82%8A%E3%81%AB%20

    plugin(function ({ addUtilities, addComponents, e, prefix, config }) {
      const newUtilities = {
        ".horizontal-tb": {
          writingMode: "horizontal-tb",
        },
        ".vertical-rl": {
          writingMode: "vertical-rl",
        },
        ".vertical-lr": {
          writingMode: "vertical-lr",
        },
      };
      addUtilities(newUtilities);
    }),

    
  ]
}
