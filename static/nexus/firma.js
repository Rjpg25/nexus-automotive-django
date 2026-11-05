"use strict";
(() => {
  const canvas = document.getElementById("firma-canvas");
  if (!canvas) return;
  const context = canvas.getContext("2d");
  const hidden = document.getElementById("id_firma");
  let drawing = false;
  let hasInk = false;
  const clear = () => {
    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.strokeStyle = "#17202c";
    context.fillStyle = "#17202c";
    context.lineWidth = 4;
    context.lineJoin = "round";
    context.lineCap = "round";
    hidden.value = "";
    hasInk = false;
  };
  const previous = hidden.value;
  clear();
  if (previous.startsWith("data:image/png;base64,")) {
    const image = new Image();
    image.onload = () => { context.drawImage(image, 0, 0, canvas.width, canvas.height); hasInk = true; };
    image.src = previous;
  }
  const point = (event) => {
    const rect = canvas.getBoundingClientRect();
    return {x: (event.clientX - rect.left) * canvas.width / rect.width, y: (event.clientY - rect.top) * canvas.height / rect.height};
  };
  canvas.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    canvas.setPointerCapture(event.pointerId);
    drawing = true;
    hasInk = true;
    const p = point(event);
    context.beginPath();
    context.arc(p.x, p.y, 2, 0, Math.PI * 2);
    context.fill();
    context.beginPath();
    context.moveTo(p.x, p.y);
  });
  canvas.addEventListener("pointermove", (event) => {
    if (!drawing) return;
    const p = point(event);
    context.lineTo(p.x, p.y);
    context.stroke();
  });
  const end = () => {drawing = false;};
  canvas.addEventListener("pointerup", end);
  canvas.addEventListener("pointercancel", end);
  document.getElementById("limpiar-firma").addEventListener("click", clear);
  document.getElementById("entrega-form").addEventListener("submit", () => {
    hidden.value = hasInk ? canvas.toDataURL("image/png") : "";
  });
})();
