/* study.js: behavior for study pages. Quiz self-scoring, flashcards, theme toggle.
   Works with no build step and no network. */
(function () {
  // Theme toggle (optional button.theme-toggle); remembered per browser when storage works.
  var root = document.documentElement, KEY = "study-theme";
  try { var saved = localStorage.getItem(KEY); if (saved) root.dataset.theme = saved; } catch (e) {}
  document.querySelectorAll(".theme-toggle").forEach(function (b) {
    b.addEventListener("click", function () {
      var dark = root.dataset.theme ? root.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
      root.dataset.theme = dark ? "light" : "dark";
      try { localStorage.setItem(KEY, root.dataset.theme); } catch (e) {}
    });
  });

  // Quiz: "Show answers" reveals every .a; "I got it" boxes count toward the score.
  document.querySelectorAll(".quiz").forEach(function (q) {
    var items = q.querySelectorAll("li");
    items.forEach(function (li) {
      if (!li.querySelector(".a")) return;
      var lab = document.createElement("label"); lab.className = "got";
      lab.innerHTML = '<input type="checkbox"> I got it';
      li.querySelector(".a").appendChild(lab);
    });
    var bar = document.createElement("div"); bar.className = "bar";
    bar.innerHTML = '<button class="btn" type="button">Show answers</button><span class="score" aria-live="polite"></span>';
    q.appendChild(bar);
    var btn = bar.querySelector("button"), score = bar.querySelector(".score");
    function update() {
      var n = q.querySelectorAll(".got input:checked").length;
      score.textContent = q.classList.contains("revealed") ? n + " / " + items.length : "";
    }
    btn.addEventListener("click", function () {
      q.classList.toggle("revealed");
      btn.textContent = q.classList.contains("revealed") ? "Hide answers" : "Show answers";
      update();
    });
    q.addEventListener("change", update);
  });

  // Flashcards
  document.querySelectorAll(".card").forEach(function (c) {
    c.tabIndex = 0; c.setAttribute("role", "button");
    function flip() { c.classList.toggle("flipped"); }
    c.addEventListener("click", flip);
    c.addEventListener("keydown", function (e) { if (e.key === " " || e.key === "Enter") { e.preventDefault(); flip(); } });
  });
})();
