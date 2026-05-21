<script setup>
import { computed, ref } from "vue";
import LoginPage from "./components/LoginPage.vue";
import StepViewer from "./components/StepViewer.vue";

const LOGIN_STORAGE_KEY = "freecad-assembler-auth";
const DEFAULT_LOGIN_USER = "admin";
const DEFAULT_LOGIN_PASSWORD = "admin123";

const isAuthed = ref(false);
const authPending = ref(false);
const authError = ref("");

const expectedUser = computed(() => (import.meta.env.VITE_LOGIN_USER || DEFAULT_LOGIN_USER).trim());
const expectedPassword = computed(() => import.meta.env.VITE_LOGIN_PASSWORD || DEFAULT_LOGIN_PASSWORD);

try {
  if (typeof window !== "undefined" && window.localStorage.getItem(LOGIN_STORAGE_KEY) === "1") {
    isAuthed.value = true;
  }
} catch {
  // Ignore storage access errors.
}

function handleLogin(payload) {
  authError.value = "";
  authPending.value = true;

  window.setTimeout(() => {
    const valid = payload.username === expectedUser.value && payload.password === expectedPassword.value;

    if (!valid) {
      authError.value = "账号或密码错误，请重试。";
      authPending.value = false;
      return;
    }

    isAuthed.value = true;
    authPending.value = false;

    try {
      if (payload.remember) {
        window.localStorage.setItem(LOGIN_STORAGE_KEY, "1");
      } else {
        window.localStorage.removeItem(LOGIN_STORAGE_KEY);
      }
    } catch {
      // Ignore storage access errors.
    }
  }, 260);
}
</script>

<template>
  <LoginPage v-if="!isAuthed" :pending="authPending" :error="authError" @submit="handleLogin" />
  <StepViewer v-else />
</template>
