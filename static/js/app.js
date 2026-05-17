document.addEventListener("click", async (event) => {
  const copyButton = event.target.closest("[data-copy-target]");
  if (copyButton) {
    const id = copyButton.getAttribute("data-copy-target");
    const target = document.getElementById(id);
    if (!target) return;
    await navigator.clipboard.writeText(target.value || target.textContent || "");
    const oldText = copyButton.textContent;
    copyButton.textContent = "Copied";
    window.setTimeout(() => {
      copyButton.textContent = oldText;
    }, 1200);
  }

  const publishButton = event.target.closest(".danger-check");
  if (publishButton) {
    const ok = window.confirm("Đăng bài này lên Facebook ngay?");
    if (!ok) {
      event.preventDefault();
    }
  }
});

