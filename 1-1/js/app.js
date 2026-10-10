// ==========================================================================
// 1. 단일 진실 공급원 (Single Source of Truth) 상태 객체
// ==========================================================================
const GITHUB_USERNAME = "octocat"; // 본인의 GitHub ID로 변경

const appState = {
  // 테마 상태
  theme: localStorage.getItem("theme") || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"),
  
  // 프로젝트 API 데이터 상태
  projects: [],
  selectedLanguage: "all",
  fetchStatus: "idle", // 'idle' | 'loading' | 'success' | 'error' | 'empty'
  errorMessage: "",

  // 폼 유효성 상태
  formValues: { name: "", email: "", message: "" },
  formErrors: { name: "", email: "", message: "" },
  formStatus: "idle" // 'idle' | 'success'
};

// ==========================================================================
// 2. 상태 렌더러 (State -> DOM Update)
// ==========================================================================

// [상태 1] 테마 렌더링
const themeToggleBtn = document.querySelector("#theme-toggle");
const renderTheme = () => {
  document.documentElement.setAttribute("data-theme", appState.theme);
  themeToggleBtn.textContent = appState.theme === "dark" ? "☀️" : "🌙";
  localStorage.setItem("theme", appState.theme);
};

// [상태 2 & 4] 프로젝트 및 필터 렌더링
const projectsContainer = document.querySelector("#projects-container");
const filterContainer = document.querySelector("#filter-container");

const renderProjects = () => {
  // 1. 로딩 상태
  if (appState.fetchStatus === "loading") {
    projectsContainer.innerHTML = `
      <div class="state-box">
        <div class="spinner"></div>
        <p>GitHub에서 프로젝트를 가져오는 중입니다...</p>
      </div>
    `;
    return;
  }

  // 2. 에러 상태 (레이트 리밋 403 포함)
  if (appState.fetchStatus === "error") {
    projectsContainer.innerHTML = `
      <div class="state-box">
        <p style="color: var(--error); margin-bottom: 1.25rem;">${appState.errorMessage}</p>
        <button id="retry-btn" class="btn btn-secondary">다시 시도</button>
      </div>
    `;
    document.querySelector("#retry-btn").addEventListener("click", fetchRepositories);
    return;
  }

  // 3. 필터링 로직 적용
  const filteredProjects = appState.selectedLanguage === "all"
    ? appState.projects
    : appState.projects.filter(p => (p.language || "Other") === appState.selectedLanguage);

  // 4. 빈 상태
  if (filteredProjects.length === 0) {
    projectsContainer.innerHTML = `
      <div class="state-box">
        <p>표시할 프로젝트가 없습니다.</p>
      </div>
    `;
    return;
  }

  // 5. 성공 상태 렌더링 (map + 구조분해 할당 + 템플릿 리터럴)
  projectsContainer.innerHTML = filteredProjects.map(({ name, description, html_url, stargazers_count, language }) => `
    <article class="project-card">
      <div class="project-header">
        <h3>${name}</h3>
        <p class="project-desc">${description || "등록된 프로젝트 설명이 없습니다."}</p>
      </div>
      <div>
        <div class="project-meta">
          <span>● ${language || "기타"}</span>
          <span>★ ${stargazers_count}</span>
        </div>
        <a href="${html_url}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary" style="width: 100%; text-align: center;">저장소 방문</a>
      </div>
    </article>
  `).join("");
};

const renderFilterButtons = () => {
  // 프로젝트에서 사용된 고유 언어 목록 추출
  const languages = ["all", ...new Set(appState.projects.map(p => p.language || "Other"))];

  filterContainer.innerHTML = languages.map(lang => `
    <button class="filter-btn ${appState.selectedLanguage === lang ? "active" : ""}" data-lang="${lang}">
      ${lang.toUpperCase()}
    </button>
  `).join("");
};

// [상태 3] 폼 유효성 에러 렌더링
const renderFormValidation = () => {
  const fields = ["name", "email", "message"];
  fields.forEach(field => {
    const inputEl = document.querySelector(`#user-${field}`);
    const errorEl = document.querySelector(`#${field}-error`);
    
    errorEl.textContent = appState.formErrors[field];
    if (appState.formErrors[field]) {
      inputEl.classList.add("invalid");
    } else {
      inputEl.classList.remove("invalid");
    }
  });

  const feedbackEl = document.querySelector("#form-feedback");
  if (appState.formStatus === "success") {
    feedbackEl.style.color = "var(--success)";
    feedbackEl.textContent = "성공적으로 메시지가 전송되었습니다!";
  } else {
    feedbackEl.textContent = "";
  }
};

// ==========================================================================
// 3. 비동기 데이터 통신 (Async/Await & Error Handling)
// ==========================================================================
const fetchRepositories = async () => {
  appState.fetchStatus = "loading";
  renderProjects();

  try {
    const response = await fetch(`https://api.github.com/users/${GITHUB_USERNAME}/repos?sort=updated&per_page=12`);

    if (response.status === 403) {
      throw new Error("GitHub API 요청 한도를 초과했습니다 (시간당 60회). 잠시 후 다시 시도해 주세요.");
    }
    if (!response.ok) {
      throw new Error("프로젝트 데이터를 가져오는 데 실패했습니다.");
    }

    const data = await response.json();
    
    if (data.length === 0) {
      appState.fetchStatus = "empty";
    } else {
      appState.projects = data;
      appState.fetchStatus = "success";
      renderFilterButtons();
    }
  } catch (error) {
    appState.fetchStatus = "error";
    appState.errorMessage = error.message;
  } finally {
    renderProjects();
  }
};

// ==========================================================================
// 4. 이벤트 바인딩 (addEventListener 사용)
// ==========================================================================

// 다크 모드 토글 이벤트
themeToggleBtn.addEventListener("click", () => {
  appState.theme = appState.theme === "dark" ? "light" : "dark";
  renderTheme();
});

// 네비게이션 & 햄버거 메뉴 이벤트
const header = document.querySelector("#header");
const hamburger = document.querySelector("#hamburger");
const navMenu = document.querySelector("#nav-menu");
const scrollTopBtn = document.querySelector("#scroll-top");

hamburger.addEventListener("click", () => {
  const isExpanded = hamburger.getAttribute("aria-expanded") === "true";
  hamburger.setAttribute("aria-expanded", !isExpanded);
  navMenu.classList.toggle("active");
});

document.querySelectorAll(".nav-link").forEach(link => {
  link.addEventListener("click", () => {
    navMenu.classList.remove("active");
    hamburger.setAttribute("aria-expanded", "false");
  });
});

// 스크롤 이벤트 (네비 스타일 변경: 60px / 스크롤 탑 버튼: 300px)
window.addEventListener("scroll", () => {
  if (window.scrollY > 60) {
    header.classList.add("scrolled");
  } else {
    header.classList.remove("scrolled");
  }

  if (window.scrollY > 300) {
    scrollTopBtn.classList.add("visible");
  } else {
    scrollTopBtn.classList.remove("visible");
  }
});

scrollTopBtn.addEventListener("click", () => {
  window.scrollTo({ top: 0, behavior: "smooth" });
});

// 프로젝트 필터링 이벤트 (이벤트 위임 패턴)
filterContainer.addEventListener("click", (e) => {
  if (!e.target.classList.contains("filter-btn")) return;
  
  appState.selectedLanguage = e.target.dataset.lang;
  renderFilterButtons();
  renderProjects();
});

// 폼 실시간 입력(input) 및 제출(submit) 이벤트
const contactForm = document.querySelector("#contact-form");
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const validateField = (name, value) => {
  if (!value.trim()) return "해당 필드를 입력해 주세요.";
  if (name === "email" && !emailRegex.test(value.trim())) return "올바른 이메일 형식이 아닙니다.";
  return "";
};

["user-name", "user-email", "user-message"].forEach(id => {
  const inputEl = document.querySelector(`#${id}`);
  const fieldName = inputEl.name;

  inputEl.addEventListener("input", (e) => {
    appState.formValues[fieldName] = e.target.value;
    appState.formErrors[fieldName] = validateField(fieldName, e.target.value);
    appState.formStatus = "idle";
    renderFormValidation();
  });
});

contactForm.addEventListener("submit", (e) => {
  e.preventDefault();

  // 최종 전체 검증
  const nameError = validateField("name", appState.formValues.name);
  const emailError = validateField("email", appState.formValues.email);
  const messageError = validateField("message", appState.formValues.message);

  appState.formErrors = { name: nameError, email: emailError, message: messageError };

  if (!nameError && !emailError && !messageError) {
    appState.formStatus = "success";
    contactForm.reset();
    appState.formValues = { name: "", email: "", message: "" };
  } else {
    appState.formStatus = "idle";
  }

  renderFormValidation();
});

// ==========================================================================
// 5. 부가 인터랙션 (Intersection Observer & 타이핑 효과)
// ==========================================================================

// 스크롤 애니메이션 옵저버
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add("in-view");
    }
  });
}, { threshold: 0.2 });

document.querySelectorAll(".section-observe").forEach(el => observer.observe(el));

// Hero 타이핑 애니메이션
const typingTarget = document.querySelector("#typing-text");
const typingText = "프론트엔드 개발자입니다.";
let charIndex = 0;

const runTypingEffect = () => {
  if (charIndex < typingText.length) {
    typingTarget.textContent += typingText.charAt(charIndex);
    charIndex++;
    setTimeout(runTypingEffect, 90);
  }
};

// ==========================================================================
// 6. 초기 실행
// ==========================================================================
renderTheme();
fetchRepositories();
runTypingEffect();