try {
  var t = localStorage.getItem("vum-tema");
  if (t) document.documentElement.dataset.theme = t;
} catch (e) {}