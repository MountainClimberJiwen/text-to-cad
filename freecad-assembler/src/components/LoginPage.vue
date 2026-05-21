<script setup>
import { computed, ref } from "vue";
import { LogIn } from "lucide-vue-next";

const props = defineProps({
  pending: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: ""
  }
});

const emit = defineEmits(["submit"]);

const username = ref("");
const password = ref("");
const remember = ref(true);

const canSubmit = computed(() => username.value.trim() && password.value && !props.pending);

function onSubmit() {
  if (!canSubmit.value) {
    return;
  }

  emit("submit", {
    username: username.value.trim(),
    password: password.value,
    remember: remember.value
  });
}
</script>

<template>
  <main class="login-page">
    <section class="login-card">
      <p class="login-eyebrow">FreeCAD Assembler</p>
      <h1 class="login-title">登录系统</h1>
      <p class="login-subtitle">请先登录后再进入装配建模工作台。</p>
      <label class="login-field">
        <span>账号</span>
        <input
          v-model="username"
          type="text"
          autocomplete="username"
          placeholder="请输入账号"
          @keydown.enter.prevent="onSubmit"
        />
      </label>
      <label class="login-field">
        <span>密码</span>
        <input
          v-model="password"
          type="password"
          autocomplete="current-password"
          placeholder="请输入密码"
          @keydown.enter.prevent="onSubmit"
        />
      </label>
      <label class="remember-line">
        <input v-model="remember" type="checkbox" />
        <span>记住登录状态</span>
      </label>
      <p v-if="error" class="login-error">{{ error }}</p>
      <button class="primary login-action" :disabled="!canSubmit" @click="onSubmit">
        <LogIn :size="16" />
        <span>{{ pending ? "登录中..." : "登录" }}</span>
      </button>
    </section>
  </main>
</template>
