// Búsqueda dinámica: pide los datos al servidor con fetch y cambia la tabla
// sin recargar la página. Si JavaScript falla, el formulario normal sigue
// funcionando porque envía la búsqueda por GET.

var formulario = document.getElementById("buscador");
var campoBusqueda = formulario.querySelector("input[name=buscar]");
var contenedor = document.getElementById("resultados");
var contador = document.getElementById("contador");
var tipo = formulario.dataset.tipo;
var temporizador = null;
var numeroPeticion = 0;

function pesos(valor) {
  return "$" + Number(valor).toLocaleString("es-CO");
}

function crear(etiqueta, clase, texto) {
  var elemento = document.createElement(etiqueta);
  if (clase) {
    elemento.className = clase;
  }
  if (texto !== undefined) {
    elemento.textContent = texto;
  }
  return elemento;
}

function celda(texto, clase) {
  return crear("td", clase || "", texto);
}

function etiquetaEstado(texto, clase) {
  var td = document.createElement("td");
  td.appendChild(crear("span", "adm-pill " + clase, texto));
  return td;
}

function filaPerfume(p) {
  var fila = document.createElement("tr");

  var tdProducto = document.createElement("td");
  var producto = crear("div", "adm-product");
  var miniatura = crear("div", "adm-thumb");
  if (p.imagen) {
    var imagen = document.createElement("img");
    imagen.src = p.imagen;
    imagen.alt = "";
    imagen.onerror = function () { imagen.style.display = "none"; };
    miniatura.appendChild(imagen);
  }
  var datos = document.createElement("div");
  var nombre = crear("div", "adm-product-name", p.nombre + " ");
  if (p.mas_vendido) {
    nombre.appendChild(crear("span", "adm-tag", "Más vendido"));
  }
  datos.appendChild(nombre);
  datos.appendChild(crear("div", "adm-product-meta", p.marca + " · " + p.familia_tag));
  producto.appendChild(miniatura);
  producto.appendChild(datos);
  tdProducto.appendChild(producto);
  fila.appendChild(tdProducto);

  fila.appendChild(celda(p.genero));
  fila.appendChild(celda(p.precio5 ? pesos(p.precio5) : "—", "num"));
  fila.appendChild(celda(p.precio10 ? pesos(p.precio10) : "—", "num"));
  fila.appendChild(celda(p.precio100 ? pesos(p.precio100) : "—", p.precio100 ? "num" : "num num-empty"));
  fila.appendChild(p.disponible ? etiquetaEstado("Disponible", "ok") : etiquetaEstado("Agotado", "out"));

  var tdAcciones = document.createElement("td");
  var acciones = crear("div", "adm-actions");
  var editar = crear("a", "adm-btn-edit", "Editar");
  editar.href = p.url_editar;
  var borrar = document.createElement("form");
  borrar.method = "post";
  borrar.action = p.url_eliminar;
  borrar.onsubmit = function () { return confirm("¿Eliminar este perfume?"); };
  var token = document.createElement("input");
  token.type = "hidden";
  token.name = "token";
  token.value = contenedor.dataset.token;
  var boton = crear("button", "adm-btn-del", "Eliminar");
  boton.type = "submit";
  borrar.appendChild(token);
  borrar.appendChild(boton);
  acciones.appendChild(editar);
  acciones.appendChild(borrar);
  tdAcciones.appendChild(acciones);
  fila.appendChild(tdAcciones);

  return fila;
}

function filaVenta(v) {
  var fila = document.createElement("tr");
  fila.appendChild(celda(v.fecha));
  fila.appendChild(celda(v.cliente));

  var tdPerfume = celda(v.perfume);
  tdPerfume.appendChild(crear("div", "adm-product-meta", v.detalle));
  fila.appendChild(tdPerfume);

  fila.appendChild(celda(pesos(v.total), "num"));
  fila.appendChild(celda(pesos(v.abonado), "num"));
  fila.appendChild(celda(pesos(v.debe), "num"));
  fila.appendChild(v.debe > 0 ? etiquetaEstado("Debe", "out") : etiquetaEstado("Pagada", "ok"));

  var tdAcciones = document.createElement("td");
  var acciones = crear("div", "adm-actions");
  var ver = crear("a", "adm-btn-edit", "Ver");
  ver.href = v.url;
  acciones.appendChild(ver);
  tdAcciones.appendChild(acciones);
  fila.appendChild(tdAcciones);

  return fila;
}

function dibujarTabla(lista, titulos, hacerFila, textoVacio) {
  contenedor.innerHTML = "";

  if (lista.length === 0) {
    contenedor.appendChild(crear("div", "adm-empty", textoVacio));
    return;
  }

  var tabla = crear("table", "adm-table");
  var encabezado = document.createElement("tr");
  titulos.forEach(function (titulo) {
    encabezado.appendChild(crear("th", "", titulo));
  });
  var thead = document.createElement("thead");
  thead.appendChild(encabezado);
  var tbody = document.createElement("tbody");
  lista.forEach(function (elemento) {
    tbody.appendChild(hacerFila(elemento));
  });
  tabla.appendChild(thead);
  tabla.appendChild(tbody);
  contenedor.appendChild(tabla);
}

function mostrar(datos) {
  var cantidad = datos.total;
  if (tipo === "perfumes") {
    contador.textContent = cantidad + (cantidad === 1 ? " perfume" : " perfumes");
    dibujarTabla(datos.perfumes, ["Perfume", "Género", "5 ML", "10 ML", "100 ML", "Estado", ""],
                 filaPerfume, "No se encontraron perfumes.");
  } else {
    contador.textContent = cantidad + (cantidad === 1 ? " venta" : " ventas");
    dibujarTabla(datos.ventas, ["Fecha", "Cliente", "Perfume", "Total", "Abonado", "Debe", "Estado", ""],
                 filaVenta, "No hay ventas para mostrar.");
  }
}

function buscar() {
  var parametros = new URLSearchParams();
  parametros.set("q", campoBusqueda.value);
  var estado = formulario.querySelector("input[name=estado]");
  if (estado) {
    parametros.set("estado", estado.value);
  }

  numeroPeticion = numeroPeticion + 1;
  var miNumero = numeroPeticion;

  fetch(formulario.dataset.api + "?" + parametros.toString(), { credentials: "same-origin" })
    .then(function (respuesta) {
      if (!respuesta.ok) {
        throw new Error("respuesta no válida");
      }
      return respuesta.json();
    })
    .then(function (datos) {
      // Si ya se hizo una búsqueda más nueva, esta respuesta se ignora
      if (miNumero === numeroPeticion) {
        mostrar(datos);
      }
    })
    .catch(function () {
      if (miNumero === numeroPeticion) {
        contenedor.innerHTML = "";
        contenedor.appendChild(crear("div", "adm-empty", "No se pudo buscar. Recarga la página e intenta de nuevo."));
      }
    });
}

campoBusqueda.addEventListener("input", function () {
  clearTimeout(temporizador);
  temporizador = setTimeout(buscar, 300);
});

formulario.addEventListener("submit", function (e) {
  e.preventDefault();
  clearTimeout(temporizador);
  buscar();
});
