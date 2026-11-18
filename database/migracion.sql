-- ============================================================
-- Noir · Migración para una base de datos que YA tiene datos
-- Sirve para quien ya importó el noir.sql original (tablas usuarios,
-- perfumes, tamanos, pedidos y detalle_pedido).
--
-- ANTES DE EJECUTAR: haz una copia desde phpMyAdmin (Exportar).
-- Es seguro correrlo más de una vez: solo crea lo que falta.
-- No borra ni modifica ningún perfume, usuario ni venta.
-- ============================================================

USE `noir`;

-- 1) Abonos de las ventas (pagos parciales)
CREATE TABLE IF NOT EXISTS `abonos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `pedido_id` int(11) NOT NULL,
  `monto` int(11) NOT NULL,
  `fecha` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `pedido_id` (`pedido_id`),
  CONSTRAINT `abonos_ibfk_1` FOREIGN KEY (`pedido_id`) REFERENCES `pedidos` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 2) Gastos del negocio
CREATE TABLE IF NOT EXISTS `gastos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `fecha` date NOT NULL,
  `concepto` varchar(120) NOT NULL,
  `categoria` varchar(40) NOT NULL,
  `monto` int(11) NOT NULL,
  `nota` varchar(255) DEFAULT NULL,
  `usuario_id` int(11) DEFAULT NULL,
  `creado` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `fecha` (`fecha`),
  KEY `usuario_id` (`usuario_id`),
  CONSTRAINT `gastos_ibfk_1` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 3) OPCIONAL: quitar la columna stock_ml, que ya no se usa.
--    Esto SÍ borra esos datos de la columna. Quita los dos guiones para ejecutarla.
-- ALTER TABLE `perfumes` DROP COLUMN `stock_ml`;
