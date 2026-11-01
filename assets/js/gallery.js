(function () {
  const IMAGE_EXTENSIONS = ["jpg", "jpeg", "png"];

  function dayNumber(day) {
    return String(day).padStart(2, "0");
  }

  function imageCandidates(year) {
    const dir = CHALLENGE_YEARS[year].imageDir;
    return (day) => IMAGE_EXTENSIONS.map((ext) => `${dir}/day-${dayNumber(day)}.${ext}`);
  }

  function buildCard(year, entry, candidates) {
    const card = document.createElement("article");
    card.className = "day-card";

    const frame = document.createElement("div");
    frame.className = "day-frame";

    const img = document.createElement("img");
    img.loading = "lazy";
    img.decoding = "async";
    img.alt = `Day ${entry.day} — ${entry.concept}`;
    let attempt = 0;
    img.addEventListener("error", function () {
      attempt += 1;
      if (attempt < candidates.length) {
        img.src = candidates[attempt];
      } else {
        frame.classList.add("day-frame--placeholder");
        img.remove();
        const placeholder = document.createElement("span");
        placeholder.className = "day-placeholder-text";
        placeholder.textContent = "Coming " + entry.date;
        frame.appendChild(placeholder);
      }
    });
    img.src = candidates[0];
    frame.appendChild(img);

    const link = document.createElement("a");
    link.href = candidates[0];
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.appendChild(frame);
    card.appendChild(link);

    img.addEventListener("error", function () {
      if (attempt >= candidates.length) {
        link.removeAttribute("href");
      }
    });

    const meta = document.createElement("div");
    meta.className = "day-meta";
    meta.innerHTML = `
      <span class="day-number">Day ${entry.day}</span>
      <span class="day-theme">${entry.theme}</span>
      <h3 class="day-concept">${entry.concept}</h3>
      <span class="day-date">${entry.date} &middot; ${entry.tool}</span>
    `;
    card.appendChild(meta);

    return card;
  }

  function renderYear(year) {
    const yearData = CHALLENGE_YEARS[year];
    const grid = document.getElementById("day-grid");
    grid.innerHTML = "";
    const makeCandidates = imageCandidates(year);
    yearData.days.forEach((entry) => {
      grid.appendChild(buildCard(year, entry, makeCandidates(entry.day)));
    });

    const planLink = document.getElementById("plan-link");
    if (planLink) {
      planLink.href = yearData.planUrl;
      planLink.hidden = !yearData.planUrl;
    }
  }

  function renderYearTabs(activeYear) {
    const tabs = document.getElementById("year-tabs");
    tabs.innerHTML = "";
    Object.keys(CHALLENGE_YEARS)
      .sort((a, b) => b - a)
      .forEach((year) => {
        const tab = document.createElement("a");
        tab.href = `?year=${year}`;
        tab.textContent = year;
        tab.className = year === String(activeYear) ? "active" : "";
        tab.addEventListener("click", (event) => {
          event.preventDefault();
          history.pushState({}, "", `?year=${year}`);
          setActiveYear(year);
        });
        tabs.appendChild(tab);
      });
  }

  function setActiveYear(year) {
    renderYearTabs(year);
    renderYear(year);
    document.title = `30 Day Map Challenge ${year} | Colin Stiles`;
  }

  function initialYear() {
    const requested = new URLSearchParams(window.location.search).get("year");
    const years = Object.keys(CHALLENGE_YEARS);
    if (requested && CHALLENGE_YEARS[requested]) {
      return requested;
    }
    return years.sort((a, b) => b - a)[0];
  }

  document.addEventListener("DOMContentLoaded", function () {
    setActiveYear(initialYear());
  });
})();
