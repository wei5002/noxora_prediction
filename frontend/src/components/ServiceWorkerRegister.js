"use client";

import { useEffect } from "react";

export default function ServiceWorkerRegister() {
  useEffect(() => {
    console.log("ServiceWorkerRegister is running");

    if (!("serviceWorker" in navigator)) {
      console.error("Browser does not support Service Workers");
      return;
    }

    navigator.serviceWorker
      .register("/sw.js")
      .then((registration) => {
        console.log("Service Worker registered:", registration.scope);
      })
      .catch((error) => {
        console.error("Failed to register Service Worker:", error);
      });
  }, []);

  return null;
}