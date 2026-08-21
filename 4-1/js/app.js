// ==========================================
// 1. 상태 및 상수 정의
// ==========================================
const GITHUB_USERNAME = "octocat"; // 본인의 GitHub 아이디로 변경

const state = {
  theme: localStorage.getItem("theme") || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"),
  projects: [],
  fetchStatus: "idle", // 'idle' | 'loading' | 'success' | 'error' | 'empty'
  errorMessage: ""
};

// ==========================================
// 2. 테마 관리 (다크 모드)
// ==========================================
const themeToggleBtn = document.querySelector("#theme-toggle");

const renderTheme = () => {
  document.documentElement.setAttribute("data-theme", state.theme);
  themeToggleBtn.textContent = state.theme === "dark" ? "☀️" : "🌙";
  localStorage.setItem("theme", state.theme);
};

themeToggleBtn.addEventListener("click", () => {
  state.theme = state.theme === "dark" ? "light" : "dark";
  renderTheme();
});

// ==========================================
// 3. 네비게이션 & 스크롤 인터랙션
// ==========================================
const header = document.querySelector("#header");
const hamburger = document.querySelector("#hamburger");
const navMenu = document.querySelector("#nav-menu");
const scrollTopBtn = document.querySelector("#scroll-top");

hamburger.addEventListener("click", () => {
  navMenu.classList.toggle("active");
});

// 메뉴 클릭 시 모바일 드롭다운 닫기
document.querySelectorAll(".nav-link").forEach(link => {
  link.addEventListener("click", () => {
    navMenu.classList.remove("active");
  });
});

window.addEventListener("scroll", () => {
  // 네비게이션 배경 스타일 전환 (60px 기준)
  if (window.scrollY > 60) {
    header.classList.add("scrolled");
  } else {
    header.classList.remove("scrolled");
  }

  // 맨 위로 가기 버튼 노출 (300px 기준)
  if (window.scrollY > 300) {
    scrollTopBtn.classList.add("visible");
  } else {
    scrollTopBtn.classList.remove("visible");
  }
});

scrollTopBtn.addEventListener("click", () => {
  window.scrollTo({ top: 0, behavior: "smooth" });
});

// ==========================================
// 4. 스크롤 인터섹션 옵저버 (스크롤 애니메이션)
// ==========================================
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add("in-view");
    }
  });
}, { threshold: 0.2 });

document.querySelectorAll(".section-observe").forEach(el => observer.observe(el));

// ==========================================
// 5. GitHub API 연동 및 상태별 렌더링
// ==========================================
const projectsContainer = document.querySelector("#projects-container");

const renderProjects = () => {
  if (state.fetchStatus === "loading") {
    projectsContainer.innerHTML = `
      <div class="state-box">
        <div class="spinner"></div>
        <p>프로젝트를 불러오는 중입니다...</p>
      </div>
    `;
    return;
  }

  if (state.fetchStatus === "error") {
    projectsContainer.innerHTML = `
      <div class="state-box">
        <p style="color: #ef4444; margin-bottom: 1rem;">${state.errorMessage}</p>
        <button id="retry-btn" class="btn btn-secondary">다시 시도</button>
      </div>
    `;
    document.querySelector("#retry-btn").addEventListener("click", fetchRepositories);
    return;
  }

  if (state.fetchStatus === "empty") {
    projectsContainer.innerHTML = `
      <div class="state-box">
        <p>표시할 프로젝트가 없습니다.</p>
      </div>
    `;
    return;
  }

  if (state.fetchStatus === "success") {
    projectsContainer.innerHTML = state.projects.map(({ name, description, html_url, stargazers_count, language }) => `
      <article class="project-card">
        <div>
          <h3>${name}</h3>
          <p>${description ? description : "프로젝트 설명이 없습니다."}</p>
        </div>
        <div class="project-meta">
          <span>${language ? language : "기타"}</span>
          <span>★ ${stargazers_count}</span>
        </div>
        <a href="${html_url}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary" style="margin-top: 1rem; text-align: center;">저장소 보기</a>
      </article>
    `).join("");
  }
};

const fetchRepositories = async () => {
  state.fetchStatus = "loading";
  renderProjects();

  try {
    const response = await fetch(`https://api.github.com/users/${GITHUB_USERNAME}/repos?sort=updated&per_page=6`);
    
    if (response.status === 403) {
      throw new Error("GitHub API 요청 한도를 초과했습니다 (403 Rate Limit). 잠시 후 다시 시도해주세요.");
    }
    if (!response.ok) {
      throw new Error("프로젝트를 불러올 수 없습니다.");
    }

    const data = await response.json();

    if (data.length === 0) {
      state.fetchStatus = "empty";
    } else {
      state.projects = data;
      state.fetchStatus = "success";
    }
  } catch (error) {
    state.fetchStatus = "error";
    state.errorMessage = error.message;
  } finally {
    renderProjects();
  }
};

// ==========================================
// 6. 폼 유효성 검증
// ==========================================
const contactForm = document.querySelector("#contact-form");
const nameInput = document.querySelector("#name");
const emailInput = document.querySelector("#email");
const messageInput = document.querySelector("#message");
const formFeedback = document.querySelector("#form-feedback");

const validateEmail = (email) => {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
};

contactForm.addEventListener("submit", (e) => {
  e.preventDefault();
  let isValid = true;

  // 이름 검증
  if (!nameInput.value.trim()) {
    document.querySelector("#name-error").textContent = "이름을 입력해주세요.";
    isValid = false;
  } else {
    document.querySelector("#name-error").textContent = "";
  }

  // 이메일 검증
  if (!emailInput.value.trim()) {
    document.querySelector("#email-error").textContent = "이메일을 입력해주세요.";
    isValid = false;
  } else if (!validateEmail(emailInput.value.trim())) {
    document.querySelector("#email-error").textContent = "올바른 이메일 형식이 아닙니다.";
    isValid = false;
  } else {
    document.querySelector("#email-error").textContent = "";
  }

  // 메시지 검증
  if (!messageInput.value.trim()) {
    document.querySelector("#message-error").textContent = "메시지를 입력해주세요.";
    isValid = false;
  } else {
    document.querySelector("#message-error").textContent = "";
  }

  if (isValid) {
    formFeedback.style.color = "#10b981";
    formFeedback.textContent = "성공적으로 메시지가 전송되었습니다!";
    contactForm.reset();
  }
});

// ==========================================
// 7. 보너스: 타이핑 효과
// ==========================================
const typeText = "프론트엔드 개발자입니다.";
const typingEl = document.querySelector("#typing-text");
let charIndex = 0;

const startTyping = () => {
  if (charIndex < typeText.length) {
    typingEl.textContent += typeText.charAt(charIndex);
    charIndex++;
    setTimeout(startTyping, 100);
  }
};

// 초기화 실행
renderTheme();
fetchRepositories();
startTyping();