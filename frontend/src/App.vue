<script setup>
import { session } from './auth'
import AppNavbar from './components/AppNavbar.vue'
</script>

<template>
  <AppNavbar v-if="session.user" />
  <main class="container py-4">
    <router-view />
  </main>
</template>
