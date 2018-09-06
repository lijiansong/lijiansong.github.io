
function handleFigureActivation(event) {
  var node = event.currentTarget;
  node.classList.toggle("zoom");
  event.stopPropagation();
}

function toggleTheme() {
  var dark = !document.documentElement.classList.contains("dark");
  setTheme(dark);
  try {
    if (window.localStorage) {
      window.localStorage.setItem("dark", dark);
    }
  }
  catch (e) {
  }
}

function updateTheme() {
  try {
    setTheme(window.localStorage.getItem("dark") == "true");
  }
  catch (e) {
  }
}

function setTheme(dark) {
  document.documentElement.classList.toggle("dark", dark);
  document.getElementById("_ddg_theme").value = dark ? "t" : "-1";
}

window.addEventListener("storage", function() {
  updateTheme();
});

if (window.localStorage) {
  updateTheme();
}


window.addEventListener(
  "load",
  function() {
    var i;
    var elements = document.querySelectorAll("figure");
    for(i=0; i!=elements.length; ++i) {
      elements[i].addEventListener("dblclick", handleFigureActivation, false);
    }
    elements = document.querySelectorAll("pre");
    for(i=0; i!=elements.length; ++i) {
      var parent = elements[i]
      if (elements[i].matches("figure pre"))
        continue;
      elements[i].addEventListener("dblclick", handleFigureActivation, false);
    }
  });

window.MathJax = {
  config: ["MMLorHTML.js"],
  jax: [
    "input/TeX",
    // "input/MathML",
    "output/SVG",
    // "output/HTML-CSS",
    // "output/NativeMML",
    "output/CommonHTML"
  ],
  extensions: [
    "tex2jax.js",
    "mml2jax.js",
    "MathMenu.js",
    // "MathZoom.js",
    // "CHTML-preview.js"
  ],
  TeX: {
    extensions: [
      "AMSmath.js",
      "AMSsymbols.js",
      "noErrors.js",
      "noUndefined.js"
    ]
  },
  displayAlign: null
};
