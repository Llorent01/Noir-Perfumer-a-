// Validación del lado del cliente para los formularios con la clase "form-validar".
// Reglas que lee de cada campo: required, type="email", minlength, min, max,
// data-igual="id" (debe ser igual a otro campo), data-menor-igual="id"
// (no puede ser mayor que otro campo) y data-max-mb (peso máximo de un archivo).

function textoDeError(campo) {
  var valor = campo.value.trim();

  if (campo.type === "file") {
    var archivo = campo.files[0];
    if (campo.required && !archivo) {
      return "Selecciona una imagen.";
    }
    if (archivo) {
      var tipos = ["image/jpeg", "image/png", "image/webp"];
      if (tipos.indexOf(archivo.type) === -1) {
        return "La imagen debe ser JPG, PNG o WEBP.";
      }
      var maximo = Number(campo.dataset.maxMb);
      if (maximo && archivo.size > maximo * 1024 * 1024) {
        return "La imagen pesa más de " + maximo + " MB.";
      }
    }
    return "";
  }

  if (campo.required && valor === "") {
    return campo.tagName === "SELECT" ? "Elige una opción." : "Este campo es obligatorio.";
  }

  if (valor === "") {
    return "";
  }

  if (campo.type === "email") {
    var formatoCorreo = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!formatoCorreo.test(valor)) {
      return "Escribe un correo válido, por ejemplo nombre@correo.com.";
    }
  }

  if (campo.minLength > 0 && campo.value.length < campo.minLength) {
    return "Debe tener mínimo " + campo.minLength + " caracteres.";
  }

  if (campo.type === "date" && campo.max !== "" && valor > campo.max) {
    return "La fecha no puede ser futura.";
  }

  if (campo.type === "number") {
    var numero = Number(valor);
    if (isNaN(numero) || valor.indexOf(".") !== -1 || valor.indexOf(",") !== -1) {
      return "Escribe un número entero.";
    }
    if (campo.min !== "" && numero < Number(campo.min)) {
      return "El valor mínimo es " + campo.min + ".";
    }
    if (campo.max !== "" && numero > Number(campo.max)) {
      return "El valor máximo es " + campo.max + ".";
    }
  }

  if (campo.dataset.igual) {
    var otro = document.getElementById(campo.dataset.igual);
    if (otro && campo.value !== otro.value) {
      return "Las contraseñas no coinciden.";
    }
  }

  if (campo.dataset.menorIgual) {
    var tope = document.getElementById(campo.dataset.menorIgual);
    if (tope && tope.value !== "" && Number(valor) > Number(tope.value)) {
      return "No puede ser mayor que el total.";
    }
  }

  return "";
}

function mensajeDe(campo) {
  var contenedor = campo.closest(".adm-money") || campo;
  var siguiente = contenedor.nextElementSibling;
  if (siguiente && siguiente.classList.contains("campo-error")) {
    return siguiente;
  }
  var mensaje = document.createElement("p");
  mensaje.className = "campo-error";
  contenedor.insertAdjacentElement("afterend", mensaje);
  return mensaje;
}

function validarCampo(campo) {
  var texto = textoDeError(campo);
  var mensaje = mensajeDe(campo);
  mensaje.textContent = texto;
  campo.classList.toggle("campo-invalido", texto !== "");
  campo.setAttribute("aria-invalid", texto !== "" ? "true" : "false");
  return texto === "";
}

function camposDe(formulario) {
  var lista = formulario.querySelectorAll("input, select, textarea");
  var campos = [];
  for (var i = 0; i < lista.length; i++) {
    var tipo = lista[i].type;
    if (tipo !== "hidden" && tipo !== "submit" && tipo !== "checkbox" && !lista[i].disabled) {
      campos.push(lista[i]);
    }
  }
  return campos;
}

function activarValidacion(formulario) {
  formulario.setAttribute("novalidate", "novalidate");
  var campos = camposDe(formulario);

  campos.forEach(function (campo) {
    campo.addEventListener("blur", function () {
      validarCampo(campo);
    });
    // Si el campo ya tenía error, se revisa mientras la persona corrige
    campo.addEventListener("input", function () {
      if (campo.classList.contains("campo-invalido")) {
        validarCampo(campo);
      }
    });
    campo.addEventListener("change", function () {
      validarCampo(campo);
    });
  });

  formulario.addEventListener("submit", function (e) {
    var primerError = null;
    campos.forEach(function (campo) {
      if (!validarCampo(campo) && primerError === null) {
        primerError = campo;
      }
    });
    if (primerError !== null) {
      e.preventDefault();
      primerError.focus();
    }
  });
}

document.addEventListener("DOMContentLoaded", function () {
  var formularios = document.querySelectorAll("form.form-validar");
  formularios.forEach(activarValidacion);
});
