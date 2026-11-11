(function () {
  const IMAGE_EXTENSIONS = ["jpg", "jpeg", "png"];

  function dayNumber(day) {
    return String(day).padStart(2, "0");
  }

  function imageCandidates(year) {
    const dir = CHALLENGE_YEARS[year].imageDir;
    return (entry) => {
      if (entry.image) {
        return [entry.image];
      }
      return IMAGE_EXTENSIONS.map((ext) => `${dir}/day-${dayNumber(entry.day)}.${ext}`);
    };
  }

  function buildGlobeFrame() {
    const frame = document.createElement("div");
    frame.className = "day-frame day-frame--globe";
    const host = document.createElement("div");
    host.id = "mars-globe";
    host.className = "mars-globe";
    host.hidden = true;
    frame.appendChild(host);
    ["assets/js/mars-texture.js", "assets/js/mars.js"].forEach((src) => {
      const script = document.createElement("script");
      script.src = src;
      script.async = false;
      frame.appendChild(script);
    });
    return frame;
  }

  function buildEmbedFrame(entry) {
    const frame = document.createElement("div");
    frame.className = "day-frame day-frame--embed";
    const iframe = document.createElement("iframe");
    const src = entry.embed.includes("?") ? `${entry.embed}&embed=1` : `${entry.embed}?embed=1`;
    iframe.src = src;
    iframe.title = `Day ${entry.day} — ${entry.concept}`;
    iframe.loading = "lazy";
    iframe.setAttribute("allowfullscreen", "");
    let embedVisible = true;
    const postVisibility = () => {
      if (iframe.contentWindow) {
        iframe.contentWindow.postMessage({ type: "cts-embed-visible", visible: embedVisible }, "*");
      }
    };
    iframe.addEventListener("load", postVisibility);
    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver(
        (entries) => {
          embedVisible = Boolean(entries[0] && entries[0].isIntersecting && entries[0].intersectionRatio >= 0.25);
          postVisibility();
        },
        { threshold: [0, 0.25, 0.5] }
      );
      observer.observe(iframe);
    }
    frame.appendChild(iframe);

    const open = document.createElement("a");
    open.className = "day-embed-open";
    open.href = entry.embed;
    open.target = "_blank";
    open.rel = "noopener noreferrer";
    open.textContent = "Open full map";
    frame.appendChild(open);
    return frame;
  }

  function buildCard(year, entry, candidates) {
    const card = document.createElement("article");
    card.className = "day-card";

    if (entry.embed) {
      card.appendChild(buildEmbedFrame(entry));
      card.appendChild(buildMeta(entry));
      return card;
    }

    if (entry.globe) {
      card.appendChild(buildGlobeFrame());
      card.appendChild(buildMeta(entry));
      return card;
    }

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

    img.addEventListener("load", function () {
      link.href = img.src;
    });
    img.addEventListener("error", function () {
      if (attempt >= candidates.length) {
        link.removeAttribute("href");
      }
    });

    card.appendChild(buildMeta(entry));
    return card;
  }

  function buildMeta(entry) {
    const meta = document.createElement("div");
    meta.className = "day-meta";
    meta.innerHTML = `
      <span class="day-number">Day ${entry.day}</span>
      <span class="day-theme">${entry.theme}</span>
      <h3 class="day-concept">${entry.concept}</h3>
      <span class="day-date">${entry.date} &middot; ${entry.tool}</span>
    `;
    return meta;
  }

  function renderYear(year) {
    const yearData = CHALLENGE_YEARS[year];
    const grid = document.getElementById("day-grid");
    grid.innerHTML = "";
    const makeCandidates = imageCandidates(year);
    yearData.days.forEach((entry) => {
      grid.appendChild(buildCard(year, entry, makeCandidates(entry)));
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
