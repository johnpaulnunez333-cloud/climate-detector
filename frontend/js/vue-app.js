const { createApp } = Vue;

createApp({
  data() {
    const el = document.getElementById("auth-app");
    return {
      mode: el.dataset.mode,
      name: "",
      email: "",
      password: "",
      confirm: "",
      loading: false,
      error: ""
    };
  },
  computed: {
    isSignup() {
      return this.mode === "signup";
    },
    title() {
      return this.isSignup ? "Create your account" : "Welcome back";
    },
    button() {
      return this.isSignup ? "Sign up" : "Log in";
    }
  },
  mounted() {
    if (window.Auth.isLoggedIn()) {
      window.location.replace("map.html");
    }
  },
  methods: {
    async submit() {
      this.error = "";
      if (this.isSignup && this.password !== this.confirm) {
        this.error = "Passwords do not match.";
        return;
      }
      this.loading = true;
      try {
        const payload = this.isSignup
          ? { name: this.name, email: this.email, password: this.password }
          : { email: this.email, password: this.password };
        const data = await window.api(this.isSignup ? "/api/signup" : "/api/login", {
          method: "POST",
          body: JSON.stringify(payload)
        });
        window.Auth.save(data.token, data.user);
        window.location.href = "map.html";
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    }
  }
}).mount("#auth-app");
