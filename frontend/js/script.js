(function () {
  const API = window.APP_CONFIG.API_URL;

  const Auth = {
    token() {
      return localStorage.getItem("cd_token");
    },
    user() {
      try {
        return JSON.parse(localStorage.getItem("cd_user"));
      } catch (e) {
        return null;
      }
    },
    save(token, user) {
      localStorage.setItem("cd_token", token);
      localStorage.setItem("cd_user", JSON.stringify(user));
    },
    clear() {
      localStorage.removeItem("cd_token");
      localStorage.removeItem("cd_user");
    },
    isLoggedIn() {
      return Boolean(this.token());
    },
    require() {
      if (!this.isLoggedIn()) {
        window.location.replace("login.html");
      }
    },
    logout() {
      this.clear();
      window.location.href = "login.html";
    }
  };

  async function api(path, options = {}) {
    const headers = { "Content-Type": "application/json" };
    if (Auth.token()) {
      headers.Authorization = "Bearer " + Auth.token();
    }
    const response = await fetch(API + path, { ...options, headers });
    const data = await response.json().catch(() => ({}));
    if (response.status === 401 || response.status === 422) {
      if (Auth.isLoggedIn() && path !== "/api/login") {
        Auth.clear();
        window.location.replace("login.html");
      }
    }
    if (!response.ok) {
      throw new Error(data.error || data.msg || "Something went wrong. Try again.");
    }
    return data;
  }

  function renderNav() {
    const box = document.getElementById("nav-links");
    if (!box) return;
    if (Auth.isLoggedIn()) {
      const user = Auth.user();
      const name = user ? user.name : "Account";
      box.innerHTML =
        '<li class="nav-item"><a class="nav-link" href="map.html">Climate map</a></li>' +
        '<li class="nav-item"><span class="nav-link disabled-name"></span></li>' +
        '<li class="nav-item"><button class="btn btn-outline-light btn-sm ms-lg-2" id="logout-btn">Log out</button></li>';
      box.querySelector(".disabled-name").textContent = name;
      document.getElementById("logout-btn").addEventListener("click", () => Auth.logout());
    } else {
      box.innerHTML =
        '<li class="nav-item"><a class="nav-link" href="login.html">Log in</a></li>' +
        '<li class="nav-item"><a class="btn btn-warning btn-sm ms-lg-2" href="signup.html">Sign up</a></li>';
    }
  }

  function wakeBackend() {
    fetch(API + "/api/health").catch(() => {});
  }

  window.Auth = Auth;
  window.api = api;

  document.addEventListener("DOMContentLoaded", () => {
    renderNav();
    wakeBackend();
    const cta = document.getElementById("hero-cta");
    if (cta) {
      cta.setAttribute("href", Auth.isLoggedIn() ? "map.html" : "signup.html");
      cta.textContent = Auth.isLoggedIn() ? "Open climate map" : "Create free account";
    }
    const year = document.getElementById("year");
    if (year) year.textContent = new Date().getFullYear();
  });
})();
