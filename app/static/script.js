/* ============================================================
   NOIR — script.js
   Reemplaza WHATSAPP_NUMBER por tu número real (con indicativo,
   sin +, sin espacios). Ej: Colombia = 57 3001234567
   ============================================================ */
const WHATSAPP_NUMBER = "573205104511";

/* ============================================================
   DATOS DE PRODUCTOS
   Un perfume = un producto. Las presentaciones son variantes:
     price5, price10  -> siempre el foco principal (decants)
     price15, price20 -> opcionales, agrégalos solo si ofreces
                          esa fragancia en esos tamaños
     full100           -> precio del frasco completo (100 ML).
                          null/ausente = esa fragancia solo
                          existe en decant, sin frasco completo
   Todas las presentaciones se eligen dentro de "Ver fragancia".
   ============================================================ */
let PRODUCTS = [];

const TICKER_MESSAGES = [
  "Perfumes 100% originales", "Decants de 5 ML y 10 ML",
  "Envíos a toda Colombia", "Empaque discreto y cuidado",
  "Prueba antes de comprar el frasco completo", "Fraccionado artesanal"
];

/* ============================================================
   HELPERS
   ============================================================ */
const fmt = n => "$" + Number(n).toLocaleString("es-CO");
const byId = id => PRODUCTS.find(p => p.id === id);

function waLink(message){
  return "https://wa.me/" + WHATSAPP_NUMBER + "?text=" + encodeURIComponent(message);
}

function svgDecant(){
  return `<svg class="ripple-svg" viewBox="0 0 120 160"><g class="bottle">
    <rect x="30" y="40" width="60" height="105" rx="5"/>
    <rect x="48" y="16" width="24" height="26" rx="2"/>
    <rect x="42" y="4" width="36" height="14" rx="3" class="bottle-cap"/>
    <line x1="38" y1="72" x2="82" y2="72" stroke-width=".6"/>
    <line x1="38" y1="92" x2="82" y2="92" stroke-width=".6"/>
    <line x1="38" y1="112" x2="82" y2="112" stroke-width=".6"/>
  </g></svg>`;
}
function svgFull(){
  return `<svg class="ripple-svg" viewBox="0 0 120 170"><g class="bottle">
    <rect x="18" y="46" width="84" height="112" rx="6"/>
    <rect x="44" y="14" width="32" height="34" rx="3"/>
    <rect x="36" y="2" width="48" height="14" rx="3" class="bottle-cap"/>
    <line x1="28" y1="82" x2="92" y2="82" stroke-width=".6"/>
    <line x1="28" y1="102" x2="92" y2="102" stroke-width=".6"/>
    <line x1="28" y1="122" x2="92" y2="122" stroke-width=".6"/>
  </g></svg>`;
}

/* ============================================================
   STATE
   ============================================================ */
let cart = []; // {id, size:'5'|'10'|'100', qty}
let selectedSize = {}; // productId -> '5' | '10'  (per card selection)
let modalProductId = null;
let modalSize = "5";

/* ============================================================
   DOM REFS
   ============================================================ */
const $ = sel => document.querySelector(sel);
const $$ = sel => Array.from(document.querySelectorAll(sel));

const bestsellerRail = $("#bestsellerRail");
const catalogGrid    = $("#catalogGrid");

/* ============================================================
   CARD BUILDERS
   ============================================================ */
// Tamaño con el que arranca cada card: 100 ML por defecto (según lo
// pedido), y si esa fragancia no tiene frasco completo, cae a 5 ML.
function defaultSizeFor(p){
  if (p.full100) return "100";
  if (p.price5) return "5";
  return "10";
}

function sizeBoxesHTML(p, activeSize){
  const entries = [];
  if (p.full100) entries.push({ size: "100", price: p.full100 });
  if (p.price5)  entries.push({ size: "5",   price: p.price5 });
  if (p.price10) entries.push({ size: "10",  price: p.price10 });
  return `
  <div class="size-boxes" data-id="${p.id}">
    ${entries.map(e => `
    <button type="button" class="size-box ${activeSize === e.size ? "active" : ""}" data-size="${e.size}">
      <span class="size-box-ml">${e.size} ML</span>
      <span class="size-box-price">${fmt(e.price)}</span>
    </button>`).join("")}
  </div>`;
}

function cardPriceHTML(size, price){
  return `<span class="card-price-size">${size} ML —</span> <span class="card-price-amount">${fmt(price)}</span>`;
}

function priceFor(p, size){
  if (size === "100") return p.full100;
  return p["price" + size];
}

// Disponibilidad: el administrador marca cada perfume como Disponible
// o Agotado desde el panel (campo "disponible" de la base de datos).
function isEffectivelyInStock(p){
  return p.inStock !== false;
}

// Todas las presentaciones que un perfume realmente ofrece, en el orden
// en que deben mostrarse: primero 5/10 ML (foco del negocio), luego
// 15/20 ML si existen, y al final 100 ML como alternativa secundaria.
function variantList(p){
  const list = [];
  if (p.price5)  list.push({ size: "5",   price: p.price5,  tier: "primary" });
  if (p.price10) list.push({ size: "10",  price: p.price10, tier: "primary" });
  if (p.price15) list.push({ size: "15",  price: p.price15, tier: "secondary" });
  if (p.price20) list.push({ size: "20",  price: p.price20, tier: "secondary" });
  if (p.full100) list.push({ size: "100", price: p.full100, tier: "full" });
  return list;
}

function decantCard(p, mode){
  // mode: 'full' -> add to cart + whatsapp buttons (featured / bestsellers)
  // mode: 'catalog' -> "Ver fragancia" button
  const size = selectedSize[p.id] || defaultSizeFor(p);
  const price = priceFor(p, size);
  const inStock = isEffectivelyInStock(p);

  // "Más vendido" y "Agotado" son estados independientes: una fragancia
  // puede ser ambas cosas a la vez (sigue siendo más vendida aunque
  // se haya agotado momentáneamente).
  const badges = `<div class="card-badges">
    ${p.bestSeller ? `<span class="card-badge">Más vendido</span>` : ""}
    ${!inStock ? `<span class="card-badge badge-outline">Agotado</span>` : ""}
  </div>`;

  const actions = mode === "full"
    ? `<div class="card-actions">
         <button type="button" class="btn btn-primary btn-sm add-cart-btn" data-id="${p.id}" ${!inStock ? "disabled" : ""}>${inStock ? "Agregar al carrito" : "Agotado"}</button>
         <a class="btn btn-whatsapp btn-sm quick-wa-btn" data-id="${p.id}" target="_blank" rel="noopener" ${!inStock ? 'disabled aria-disabled="true"' : ""}>
           <img src="/static/assets/whatsapp.svg" alt="" aria-hidden="true">
           ${inStock ? "Comprar por WhatsApp" : "Agotado"}
         </a>
       </div>`
    : `<div class="card-actions">
         <button type="button" class="btn btn-outline btn-sm btn-block view-btn" data-id="${p.id}">Ver fragancia</button>
       </div>`;

  return `
  <article class="card" data-card-id="${p.id}" tabindex="0" role="button" aria-label="Ver ${p.name}">
    <div class="card-media">
      ${badges}
      <img src="${p.image}" alt="${p.name}">
    </div>
    <div class="card-body">
      <span class="card-brand">${p.brand}</span>
      <h3 class="card-name">${p.name}</h3>
      <span class="card-family">${p.family}</span>
      <div class="card-price">${cardPriceHTML(size, price)}</div>
      <div class="size-label">Tamaño: <strong>${size} ML</strong></div>
      ${sizeBoxesHTML(p, size)}
      ${actions}
    </div>
  </article>`;
}

/* ============================================================
   RENDER
   ============================================================ */
function renderBestsellers(){
  const items = PRODUCTS.filter(p => p.bestSeller);
  bestsellerRail.innerHTML = items.map(p => decantCard(p, "full")).join("");
}

function renderCatalog(list){
  catalogGrid.innerHTML = list.length
    ? list.map(p => decantCard(p, "catalog")).join("")
    : `<p class="empty-state">No encontramos fragancias con esos filtros. Intenta ajustar tu búsqueda.</p>`;
  $("#filtersCount").textContent = list.length ? `${list.length} fragancias` : "";
}

function renderTicker(){
  const seq = [...TICKER_MESSAGES, ...TICKER_MESSAGES];
  $("#tickerTrack").innerHTML = seq.map(t => `<span class="ticker-item">${t}</span>`).join("");
}

function populateFilters(){
  const brands = [...new Set(PRODUCTS.map(p => p.brand))].sort();
  const families = [...new Set(PRODUCTS.map(p => p.familyTag))].sort();
  const brandSel = $("#filterBrand");
  const familySel = $("#filterFamily");
  brands.forEach(b => brandSel.insertAdjacentHTML("beforeend", `<option value="${b}">${b}</option>`));
  families.forEach(f => familySel.insertAdjacentHTML("beforeend", `<option value="${f}">${f}</option>`));
}

/* ============================================================
   FILTERS
   ============================================================ */
let bestsellerOnly = false;
let stockOnly = false;

function applyFilters(){
  const brand = $("#filterBrand").value;
  const gender = $("#filterGender").value;
  const family = $("#filterFamily").value;
  const priceRange = $("#filterPrice").value;
  const query = $("#catalogSearch").value.trim().toLowerCase();

  let list = PRODUCTS.filter(p => {
    if (brand && p.brand !== brand) return false;
    if (gender && p.gender !== gender) return false;
    if (family && p.familyTag !== family) return false;
    if (bestsellerOnly && !p.bestSeller) return false;
    if (stockOnly && !isEffectivelyInStock(p)) return false;
    if (query && !(p.name.toLowerCase().includes(query) || p.brand.toLowerCase().includes(query))) return false;
    if (priceRange){
      const [min, max] = priceRange.split("-").map(Number);
      if (p.price5 < min || p.price5 > max) return false;
    }
    return true;
  });

  renderCatalog(list);
  attachCatalogCardEvents();
}

/* ============================================================
   CART LOGIC
   ============================================================ */
function addToCart(id, size, qty = 1){
  const p = byId(id);
  if (!p || !isEffectivelyInStock(p)) return; // una fragancia agotada no puede comprarse
  const existing = cart.find(c => c.id === id && c.size === size);
  if (existing){ existing.qty += qty; }
  else { cart.push({ id, size, qty }); }
  renderCart();
  showToast(`${p.name} — ${size} ML agregado al carrito`);
}

function removeFromCart(id, size){
  cart = cart.filter(c => !(c.id === id && c.size === size));
  renderCart();
}

function changeQty(id, size, delta){
  const item = cart.find(c => c.id === id && c.size === size);
  if (!item) return;
  item.qty += delta;
  if (item.qty <= 0){ removeFromCart(id, size); return; }
  renderCart();
}

function cartTotal(){
  return cart.reduce((sum, c) => {
    const p = byId(c.id);
    return sum + priceFor(p, c.size) * c.qty;
  }, 0);
}

function variantLabel(size){
  return size === "100" ? "Perfume completo — 100 ML" : `Decant — ${size} ML`;
}

function renderCart(){
  const countEl = $("#cartCount");
  const totalQty = cart.reduce((s, c) => s + c.qty, 0);
  countEl.textContent = totalQty;

  const itemsEl = $("#cartItems");
  if (!cart.length){
    itemsEl.innerHTML = `<div class="cart-empty">Tu carrito está vacío.<br>Explora nuestros decants y encuentra tu próxima fragancia.</div>`;
  } else {
    itemsEl.innerHTML = cart.map(c => {
      const p = byId(c.id);
      const price = priceFor(p, c.size);
      return `
      <div class="cart-item" data-id="${c.id}" data-size="${c.size}">
        <div class="cart-item-media"><img src="${p.image}" alt="${p.name}"></div>
        <div class="cart-item-info">
          <div class="cart-item-name">${p.name}</div>
          <div class="cart-item-variant">${variantLabel(c.size)}</div>
          <div class="cart-item-row">
            <div class="qty-control">
              <button type="button" class="qty-minus">−</button>
              <span>${c.qty}</span>
              <button type="button" class="qty-plus">+</button>
            </div>
            <div class="cart-item-price">${fmt(price * c.qty)}</div>
          </div>
          <button type="button" class="cart-item-remove">Eliminar</button>
        </div>
      </div>`;
    }).join("");
  }

  $("#cartSubtotal").textContent = fmt(cartTotal());

  const waMsg = buildCartWhatsappMessage();
  $("#cartWhatsappBtn").href = waLink(waMsg);

  attachCartItemEvents();
}

function buildCartWhatsappMessage(){
  if (!cart.length){
    return "Hola, quiero conocer más sobre las fragancias de Noir.";
  }
  let msg = "Hola, quiero realizar este pedido:\n\n";
  cart.forEach(c => {
    const p = byId(c.id);
    const price = priceFor(p, c.size);
    msg += `Perfume: ${p.name}\nPresentación: ${c.size === "100" ? "100 ML (frasco completo)" : c.size + " ML (decant)"}\nCantidad: ${c.qty}\nPrecio: ${fmt(price * c.qty)}\n\n`;
  });
  msg += `Total del pedido: ${fmt(cartTotal())}`;
  return msg;
}

function attachCartItemEvents(){
  $$(".cart-item").forEach(el => {
    const id = Number(el.dataset.id);
    const size = el.dataset.size;
    el.querySelector(".qty-minus").addEventListener("click", () => changeQty(id, size, -1));
    el.querySelector(".qty-plus").addEventListener("click", () => changeQty(id, size, 1));
    el.querySelector(".cart-item-remove").addEventListener("click", () => removeFromCart(id, size));
  });
}

/* ============================================================
   CARD EVENTS (size toggle, add to cart, quick whatsapp, view)
   ============================================================ */
function attachSizeBoxEvents(scopeEl){
  scopeEl.querySelectorAll(".size-boxes").forEach(grid => {
    const id = Number(grid.dataset.id);
    grid.querySelectorAll(".size-box").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const newSize = btn.dataset.size;
        selectedSize[id] = newSize;
        grid.querySelectorAll(".size-box").forEach(b => b.classList.toggle("active", b === btn));
        const card = grid.closest(".card");
        const p = byId(id);
        const price = priceFor(p, newSize);
        const priceEl = card.querySelector(".card-price");
        if (priceEl) priceEl.innerHTML = cardPriceHTML(newSize, price);
        const labelStrong = card.querySelector(".size-label strong");
        if (labelStrong) labelStrong.textContent = `${newSize} ML`;
      });
    });
  });
}

function attachAddCartEvents(scopeEl){
  scopeEl.querySelectorAll(".add-cart-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = Number(btn.dataset.id);
      const p = byId(id);
      const size = selectedSize[id] || defaultSizeFor(p);
      addToCart(id, size, 1);
      openCart();
    });
  });
  scopeEl.querySelectorAll(".quick-wa-btn").forEach(btn => {
    btn.addEventListener("click", (e) => e.stopPropagation());
    const id = Number(btn.dataset.id);
    const p = byId(id);
    if (!isEffectivelyInStock(p)) return; // agotado: el botón queda deshabilitado, sin acción
    const size = selectedSize[id] || defaultSizeFor(p);
    const price = priceFor(p, size);
    const presentacion = size === "100" ? "100 ML (frasco completo)" : `${size} ML (decant)`;
    const msg = `Hola, quiero realizar este pedido:\n\nPerfume: ${p.name}\nPresentación: ${presentacion}\nCantidad: 1\nPrecio: ${fmt(price)}`;
    btn.href = waLink(msg);
  });
}

function attachViewEvents(scopeEl){
  scopeEl.querySelectorAll(".view-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      openModal(Number(btn.dataset.id));
    });
  });
  scopeEl.querySelectorAll(".card-name").forEach(el => {
    el.style.cursor = "pointer";
    el.addEventListener("click", (e) => {
      e.stopPropagation();
      const card = el.closest("[data-card-id]");
      if (card) openModal(Number(card.dataset.cardId));
    });
  });
}

// Toda la card es clickeable para abrir la ficha de la fragancia.
// Los controles internos (tamaños, agregar al carrito, whatsapp, ver
// fragancia) detienen la propagación del click para no chocar con esto.
function attachCardClickEvents(scopeEl){
  scopeEl.querySelectorAll(".card[data-card-id]").forEach(card => {
    const id = Number(card.dataset.cardId);
    card.addEventListener("click", () => openModal(id));
    card.addEventListener("keydown", (e) => {
      if ((e.key === "Enter" || e.key === " ") && e.target === card){
        e.preventDefault();
        openModal(id);
      }
    });
  });
}

function attachAllCardEvents(scopeEl){
  attachCardClickEvents(scopeEl);
  attachSizeBoxEvents(scopeEl);
  attachAddCartEvents(scopeEl);
  attachViewEvents(scopeEl);
}

function attachCatalogCardEvents(){ attachAllCardEvents(catalogGrid); }

/* ============================================================
   MODAL
   ============================================================ */
function openModal(id){
  modalProductId = id;
  const p = byId(id);
  const variants = variantList(p);
  // arranca en la primera presentación disponible (normalmente 5 ML)
  modalSize = variants.length ? variants[0].size : "5";

  $("#modalMedia").querySelector(".modal-product-image")?.remove();
  $("#modalMedia").insertAdjacentHTML(
    "beforeend",
    `<img class="modal-product-image" src="${p.image}" alt="${p.name}">`
  );
  $("#modalBrand").textContent = p.brand;
  $("#modalName").textContent = p.name;
  $("#modalDesc").textContent = p.desc;
  $("#modalNotes").textContent = p.notes;

  renderModalVariants();

  const inStock = isEffectivelyInStock(p);
  const addBtn = $("#modalAddCart");
  addBtn.textContent = inStock ? "Agregar al carrito" : "Agotado";
  addBtn.disabled = !inStock;
  addBtn.onclick = inStock ? () => { addToCart(p.id, modalSize, 1); } : null;

  const waBtn = $("#modalWhatsapp");
  if (inStock){
    waBtn.removeAttribute("disabled");
    waBtn.removeAttribute("aria-disabled");
  } else {
    waBtn.setAttribute("disabled", "");
    waBtn.setAttribute("aria-disabled", "true");
    waBtn.removeAttribute("href");
  }

  $("#modalOverlay").classList.add("open");
  document.body.style.overflow = "hidden";
}

// Construye el selector de presentaciones dentro de "Ver fragancia":
// 5/10 ML con protagonismo, 15/20 ML más discretos (solo si existen),
// y 100 ML como una fila separada y claramente secundaria.
function renderModalVariants(){
  const p = byId(modalProductId);
  const variants = variantList(p);
  const primary   = variants.filter(v => v.tier === "primary");
  const secondary = variants.filter(v => v.tier === "secondary");
  const full      = variants.filter(v => v.tier === "full");

  const optBtn = (v, extraClass) => `
    <button type="button" class="size-opt ${extraClass} ${modalSize === v.size ? "active" : ""}" data-size="${v.size}">${v.size} ML</button>`;

  let html = "";
  if (primary.length){
    html += `<div class="variant-group"><div class="size-toggle">${primary.map(v => optBtn(v, "size-opt-primary")).join("")}</div></div>`;
  }
  if (secondary.length){
    html += `<div class="variant-group">
      <span class="variant-group-label">Presentaciones adicionales</span>
      <div class="size-toggle">${secondary.map(v => optBtn(v, "size-opt-secondary")).join("")}</div>
    </div>`;
  }
  if (full.length){
    html += `<div class="variant-full-wrap">
      <span class="variant-group-label">Perfume completo</span>
      ${full.map(v => `
      <button type="button" class="variant-full ${modalSize === v.size ? "active" : ""}" data-size="${v.size}">
        <span class="variant-full-label">100 ML — frasco original</span>
        <span class="variant-full-price">${fmt(v.price)}</span>
      </button>`).join("")}
    </div>`;
  }

  $("#modalSizeToggle").innerHTML = html;
  $("#modalSizeToggle").querySelectorAll("[data-size]").forEach(btn => {
    btn.addEventListener("click", () => {
      modalSize = btn.dataset.size;
      renderModalVariants();
      updateModalPrice();
    });
  });
  updateModalPrice();
}

function updateModalPrice(){
  const p = byId(modalProductId);
  const price = priceFor(p, modalSize);
  const isFull = modalSize === "100";
  $("#modalPrice").innerHTML = `${fmt(price)} <small style="font-family:var(--font-body); font-size:.62rem; color:var(--muted); letter-spacing:.1em;">/ ${modalSize} ML</small>`;
  if (isEffectivelyInStock(p)){
    const presentacion = isFull ? "100 ML (frasco completo)" : `${modalSize} ML (decant)`;
    const msg = `Hola, quiero realizar este pedido:\n\nPerfume: ${p.name}\nPresentación: ${presentacion}\nCantidad: 1\nPrecio: ${fmt(price)}`;
    $("#modalWhatsapp").href = waLink(msg);
  }
}

function closeModal(){
  $("#modalOverlay").classList.remove("open");
  document.body.style.overflow = "";
}

/* ============================================================
   CART DRAWER OPEN / CLOSE
   ============================================================ */
function openCart(){
  closeModal();
  $("#cartDrawer").classList.add("open");
  $("#overlay").classList.add("open");
  document.body.style.overflow = "hidden";
}
function closeCart(){
  $("#cartDrawer").classList.remove("open");
  $("#overlay").classList.remove("open");
  document.body.style.overflow = "";
}

/* ============================================================
   CARRUSEL "MÁS VENDIDOS"
   ============================================================ */
function initCarousel(){
  const rail = $("#bestsellerRail");
  const prevBtn = $("#carouselPrev");
  const nextBtn = $("#carouselNext");
  const dotsWrap = $("#carouselDots");
  if (!rail || !rail.children.length) return;

  function maxScroll(){ return Math.max(0, rail.scrollWidth - rail.clientWidth); }

  function buildDots(){
    const ms = maxScroll();
    const pages = ms > 4 ? Math.max(2, Math.ceil(rail.scrollWidth / rail.clientWidth)) : 1;
    dotsWrap.innerHTML = Array.from({ length: pages }).map((_, i) =>
      `<button type="button" class="carousel-dot" data-i="${i}" aria-label="Ir al grupo ${i + 1}"></button>`
    ).join("");
    dotsWrap.querySelectorAll(".carousel-dot").forEach(dot => {
      dot.addEventListener("click", () => {
        const i = Number(dot.dataset.i);
        rail.scrollTo({ left: (maxScroll() / Math.max(pages - 1, 1)) * i, behavior: "smooth" });
      });
    });
    updateState();
  }

  function updateState(){
    const ms = maxScroll();
    const dots = dotsWrap.querySelectorAll(".carousel-dot");
    const idx = ms > 0 ? Math.round((rail.scrollLeft / ms) * (dots.length - 1)) : 0;
    dots.forEach((d, i) => d.classList.toggle("active", i === idx));
    if (prevBtn) prevBtn.disabled = rail.scrollLeft <= 4;
    if (nextBtn) nextBtn.disabled = rail.scrollLeft >= ms - 4;
  }

  prevBtn?.addEventListener("click", () => rail.scrollBy({ left: -rail.clientWidth * 0.9, behavior: "smooth" }));
  nextBtn?.addEventListener("click", () => rail.scrollBy({ left: rail.clientWidth * 0.9, behavior: "smooth" }));
  rail.addEventListener("scroll", updateState, { passive: true });
  window.addEventListener("resize", buildDots);

  buildDots();
}

/* ============================================================
   CARRUSEL DE IMÁGENES — sección Inicio
   Usa las fotos que ya existen en el catálogo, rotando
   automáticamente con una transición suave (crossfade).
   Indicador escalable: contador "01 / N" + barra de progreso +
   flechas — sin importar cuántos perfumes haya en el catálogo,
   nunca genera una fila de puntos.
   ============================================================ */
function initHeroCarousel(){
  const outer = $("#heroCarousel");
  const wrap = $("#heroCarouselSlides");
  const counterEl = $("#heroCarouselCounter");
  const fillEl = $("#heroCarouselProgressFill");
  const prevBtn = $("#heroCarouselPrev");
  const nextBtn = $("#heroCarouselNext");
  if (!outer || !wrap) return;

  const images = PRODUCTS.filter(p => p.image).map(p => ({ src: p.image, alt: p.name }));
  if (!images.length) return;

  wrap.innerHTML = images.map((img, i) =>
    `<img class="hero-carousel-slide ${i === 0 ? "active" : ""}" src="${img.src}" alt="${img.alt}" loading="${i === 0 ? "eager" : "lazy"}">`
  ).join("");

  const slides = Array.from(wrap.children);
  const total = slides.length;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const DWELL = 4800;
  let idx = 0;
  let timer;

  function pad(n){ return String(n).padStart(2, "0"); }

  function updateCounter(){
    if (counterEl) counterEl.textContent = `${pad(idx + 1)} / ${pad(total)}`;
  }

  function runProgress(){
    if (!fillEl || reduceMotion) return;
    fillEl.style.transition = "none";
    fillEl.style.width = "0%";
    void fillEl.offsetWidth; // fuerza reflow para reiniciar la transición
    fillEl.style.transition = `width ${DWELL}ms linear`;
    fillEl.style.width = "100%";
  }

  function goTo(i){
    slides[idx]?.classList.remove("active");
    idx = (i + total) % total;
    slides[idx]?.classList.add("active");
    updateCounter();
    runProgress();
  }

  function startAuto(){
    if (reduceMotion || total < 2) return;
    clearInterval(timer);
    timer = setInterval(() => goTo(idx + 1), DWELL);
  }

  if (total < 2){
    prevBtn?.setAttribute("disabled", "");
    nextBtn?.setAttribute("disabled", "");
  } else {
    prevBtn?.addEventListener("click", () => { goTo(idx - 1); startAuto(); });
    nextBtn?.addEventListener("click", () => { goTo(idx + 1); startAuto(); });
  }

  outer.addEventListener("mouseenter", () => clearInterval(timer));
  outer.addEventListener("mouseleave", startAuto);

  updateCounter();
  runProgress();
  startAuto();
}

/* ============================================================
   TOAST
   ============================================================ */
let toastTimer;
function showToast(text){
  const toast = $("#toast");
  $("#toastText").textContent = text;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 2600);
}

/* ============================================================
   MOBILE NAV / SEARCH
   ============================================================ */
function initNav(){
  $("#navToggle").addEventListener("click", () => $("#mobileNav").classList.add("open"));
  $("#navClose").addEventListener("click", () => $("#mobileNav").classList.remove("open"));
  $$("#mobileNav a").forEach(a => a.addEventListener("click", () => $("#mobileNav").classList.remove("open")));

  $("#searchToggle").addEventListener("click", () => {
    $("#searchWrap").classList.toggle("open");
    if ($("#searchWrap").classList.contains("open")) $("#searchInput").focus();
  });
  $("#searchInput").addEventListener("keydown", e => {
    if (e.key === "Enter"){
      $("#catalogSearch").value = $("#searchInput").value;
      document.getElementById("decants").scrollIntoView({ behavior: "smooth" });
      applyFilters();
    }
  });
  $("#mobileSearchInput").addEventListener("keydown", e => {
    if (e.key === "Enter"){
      $("#catalogSearch").value = $("#mobileSearchInput").value;
      $("#mobileNav").classList.remove("open");
      document.getElementById("decants").scrollIntoView({ behavior: "smooth" });
      applyFilters();
    }
  });
}

/* ============================================================
   REVEAL ON SCROLL
   ============================================================ */
function initReveal(){
  const els = $$(".reveal");
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting){
        e.target.classList.add("is-visible");
        obs.unobserve(e.target);
      }
    });
  }, { threshold: 0.15 });
  els.forEach(el => obs.observe(el));
}

/* ============================================================
   INIT
   ============================================================ */
function initWhatsappLinks(){
  const generalMsg = "Hola, quiero conocer más sobre las fragancias de Noir.";
  $("#headerWhatsapp").href = waLink(generalMsg);
  $("#fabWhatsapp").href = waLink(generalMsg);
  $("#contactWhatsappBtn").href = waLink(generalMsg);
  $("#contactWhatsappText").textContent = "+" + WHATSAPP_NUMBER.replace(/(\d{2})(\d{3})(\d{3})(\d{4})/, "$1 $2 $3 $4");
}

function init(){
  populateFilters();
  renderTicker();
  renderBestsellers();
  renderCatalog(PRODUCTS);
  renderCart();
  initWhatsappLinks();
  initNav();
  initReveal();
  initCarousel();
  initHeroCarousel();

  attachAllCardEvents(bestsellerRail);
  attachAllCardEvents(catalogGrid);

  // Filters
  ["filterBrand","filterGender","filterFamily","filterPrice"].forEach(id => {
    $("#" + id).addEventListener("change", applyFilters);
  });
  $("#catalogSearch").addEventListener("input", applyFilters);
  $("#filterBestseller").addEventListener("click", (e) => {
    bestsellerOnly = !bestsellerOnly;
    e.target.classList.toggle("active", bestsellerOnly);
    applyFilters();
  });
  $("#filterStock").addEventListener("click", (e) => {
    stockOnly = !stockOnly;
    e.target.classList.toggle("active", stockOnly);
    applyFilters();
  });

  // Cart drawer
  $("#cartToggle").addEventListener("click", openCart);
  $("#cartClose").addEventListener("click", closeCart);

  // Cuenta / login
  $("#accountToggle").addEventListener("click", () => { location.href = "/cuenta"; });

  $("#overlay").addEventListener("click", () => { closeCart(); closeModal(); });

  // Modal
  $("#modalClose").addEventListener("click", closeModal);
  $("#modalOverlay").addEventListener("click", (e) => { if (e.target.id === "modalOverlay") closeModal(); });
  document.addEventListener("keydown", e => { if (e.key === "Escape"){ closeModal(); closeCart(); } });

  // Contact form (demo only — no backend)
  $("#contactForm").addEventListener("submit", (e) => {
    e.preventDefault();
    const name = $("#cfName").value;
    const msg = $("#cfMsg").value;
    const waMsg = `Hola, soy ${name}. ${msg}`;
    window.open(waLink(waMsg), "_blank");
    e.target.reset();
  });
}

document.addEventListener("DOMContentLoaded", () => {
  fetch("/api/perfumes")
    .then(res => res.json())
    .then(datos => {
      PRODUCTS = datos;
      init();
    })
    .catch(() => {
      catalogGrid.innerHTML = '<p class="empty-state">No se pudo cargar el catálogo. Revisa que la base de datos esté encendida</p>';
    });
});