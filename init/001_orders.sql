CREATE TABLE IF NOT EXISTS orders (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    businessid BIGINT,
    name_shipping VARCHAR(255),
    NIT VARCHAR(50),
    address_shipping VARCHAR(255),
    statusid BIGINT,
    date_request DATETIME,
    phone_shipping VARCHAR(50),
    email_shipping VARCHAR(255),
    city_shipping VARCHAR(100),
    region_shipping VARCHAR(100),
    weight DECIMAL(10,2),
    payment_method VARCHAR(50),
    sourceid BIGINT,
    total DECIMAL(10,2),
    voided TINYINT(1) DEFAULT 0,
    metadata JSON,
    delivery_time VARCHAR(100),
    created_by BIGINT,
    updated_by BIGINT,
    instagram_user VARCHAR(100),
    facebook_name VARCHAR(100),
    tiktok_user VARCHAR(100),
    guia VARCHAR(100),
    no_factura VARCHAR(100),
    guia_link VARCHAR(255),
    id_source BIGINT,
    source_guia_id BIGINT,
    source_name_id BIGINT,
    status_shipping_id BIGINT,
    status_payment_id BIGINT,
    comment TEXT,
    shipping_method_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    orderid BIGINT NOT NULL,
    product_sku VARCHAR(100),
    product_name VARCHAR(255),
    quantity INT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (orderid) REFERENCES orders(id)
);


-- Datos dummy
-- Más datos dummy (10 órdenes)
INSERT INTO orders (businessid, name_shipping, NIT, address_shipping, statusid, date_request,
    phone_shipping, email_shipping, city_shipping, region_shipping, weight,
    payment_method, sourceid, total, voided, metadata, delivery_time, created_by, updated_by,
    instagram_user, facebook_name, tiktok_user, guia, no_factura, guia_link, id_source,
    source_guia_id, source_name_id, status_shipping_id, status_payment_id, comment, shipping_method_id)
VALUES
(3, 'Carlos Gómez', '9876543-1', 'Zona 1, Guatemala', 1, NOW(),
 '5555-1111', 'carlos@example.com', 'Guatemala', 'Guatemala', 3.0,
 'tarjeta', 12, 250.00, 0, '{"gift":"yes"}', '5 días', 3, 3,
 'carlos_insta', 'carlos_fb', 'carlos_tiktok', 'G789', 'F003', 'http://example.com/guia/3', 3,
 103, 203, 1, 1, 'Urgente, entregar hoy', 1),

(4, 'Lucía Méndez', 'CF', 'Zona 14, Guatemala', 2, NOW(),
 '5555-2222', 'lucia@example.com', 'Guatemala', 'Guatemala', 0.8,
 'efectivo', 13, 80.00, 0, '{"promo":"navidad"}', '1 día', 4, 4,
 'lucia_insta', 'lucia_fb', 'lucia_tiktok', 'G101', 'F004', 'http://example.com/guia/4', 4,
 104, 204, 2, 2, 'Cliente frecuente', 2),

(5, 'Pedro Ramírez', '456789-0', 'Zona 7, Guatemala', 3, NOW(),
 '5555-3333', 'pedro@example.com', 'Mixco', 'Guatemala', 5.5,
 'transferencia', 14, 1200.00, 0, '{"vip":"true"}', '7 días', 5, 5,
 'pedro_insta', 'pedro_fb', 'pedro_tiktok', 'G102', 'F005', 'http://example.com/guia/5', 5,
 105, 205, 3, 3, 'Verificar pago antes de entrega', 3),

(6, 'Ana Torres', 'CF', 'San Cristóbal, Mixco', 1, NOW(),
 '5555-4444', 'ana@example.com', 'Mixco', 'Guatemala', 2.0,
 'tarjeta', 15, 220.00, 0, '{"color":"azul"}', '2 días', 6, 6,
 'ana_insta', 'ana_fb', 'ana_tiktok', 'G103', 'F006', 'http://example.com/guia/6', 6,
 106, 206, 1, 1, 'Cliente nuevo', 1),

(7, 'Luis Morales', '112233-4', 'Antigua Guatemala', 2, NOW(),
 '5555-5555', 'luis@example.com', 'Antigua', 'Sacatepéquez', 1.0,
 'efectivo', 16, 95.00, 0, '{"envio":"express"}', '1 día', 7, 7,
 'luis_insta', 'luis_fb', 'luis_tiktok', 'G104', 'F007', 'http://example.com/guia/7', 7,
 107, 207, 2, 2, 'Entregar en hotel', 2),

(8, 'Sofía Herrera', '998877-6', 'Zona 18, Guatemala', 3, NOW(),
 '5555-6666', 'sofia@example.com', 'Guatemala', 'Guatemala', 4.2,
 'tarjeta', 17, 450.00, 0, '{"fragil":"yes"}', '4 días', 8, 8,
 'sofia_insta', 'sofia_fb', 'sofia_tiktok', 'G105', 'F008', 'http://example.com/guia/8', 8,
 108, 208, 3, 3, 'Producto delicado', 3),

(9, 'Andrés Castillo', '334455-7', 'Zona 9, Guatemala', 1, NOW(),
 '5555-7777', 'andres@example.com', 'Guatemala', 'Guatemala', 6.0,
 'transferencia', 18, 900.00, 0, '{"cliente":"corporativo"}', '10 días', 9, 9,
 'andres_insta', 'andres_fb', 'andres_tiktok', 'G106', 'F009', 'http://example.com/guia/9', 9,
 109, 209, 1, 1, 'Factura a nombre de empresa', 1),

(10, 'Marta Rodríguez', 'CF', 'Amatitlán, Guatemala', 2, NOW(),
 '5555-8888', 'marta@example.com', 'Amatitlán', 'Guatemala', 2.7,
 'efectivo', 19, 175.00, 0, '{"promo":"verano"}', '3 días', 10, 10,
 'marta_insta', 'marta_fb', 'marta_tiktok', 'G107', 'F010', 'http://example.com/guia/10', 10,
 110, 210, 2, 2, 'Llamar antes de entregar', 2),

(11, 'José Martínez', '556677-8', 'Escuintla, Escuintla', 3, NOW(),
 '5555-9999', 'jose@example.com', 'Escuintla', 'Escuintla', 8.0,
 'tarjeta', 20, 1600.00, 0, '{"vip":"yes"}', '12 días', 11, 11,
 'jose_insta', 'jose_fb', 'jose_tiktok', 'G108', 'F011', 'http://example.com/guia/11', 11,
 111, 211, 3, 3, 'Revisar producto al recibir', 3),

(12, 'Elena Ruiz', '223344-5', 'Chimaltenango, Guatemala', 1, NOW(),
 '5555-0000', 'elena@example.com', 'Chimaltenango', 'Chimaltenango', 1.5,
 'efectivo', 21, 130.00, 0, '{"notas":"urgente"}', '2 días', 12, 12,
 'elena_insta', 'elena_fb', 'elena_tiktok', 'G109', 'F012', 'http://example.com/guia/12', 12,
 112, 212, 1, 1, 'Enviar confirmación por correo', 1);


-- Items para order_id 1
INSERT INTO order_items (orderid, product_sku, product_name, quantity, price, subtotal)
VALUES
(1, 'SKU-1001', 'Camiseta Roja', 2, 100.00, 200.00),
(1, 'SKU-1002', 'Gorra Negra', 1, 50.00, 50.00);

-- Items para order_id 2
INSERT INTO order_items (orderid, product_sku, product_name, quantity, price, subtotal)
VALUES
(2, 'SKU-1003', 'Zapatos Deportivos', 1, 120.00, 120.00),
(2, 'SKU-1004', 'Calcetines', 2, 15.00, 30.00);

-- Items para order_id 3
INSERT INTO order_items (orderid, product_sku, product_name, quantity, price, subtotal)
VALUES
(3, 'SKU-1005', 'Laptop', 1, 300.00, 300.00);

-- Items para order_id 4
INSERT INTO order_items (orderid, product_sku, product_name, quantity, price, subtotal)
VALUES
(4, 'SKU-1006', 'Bolso', 1, 80.00, 80.00);

-- Items para order_id 5
INSERT INTO order_items (orderid, product_sku, product_name, quantity, price, subtotal)
VALUES
(5, 'SKU-1007', 'Sofá 3 plazas', 1, 1200.00, 1200.00);

-- Items para order_id 6
INSERT INTO order_items (orderid, product_sku, product_name, quantity, price, subtotal)
VALUES
(6, 'SKU-1008', 'Cámara Fotográfica', 1, 220.00, 220.00);

-- Items para order_id 7
INSERT INTO order_items (orderid, product_sku, product_name, quantity, price, subtotal)
VALUES
(7, 'SKU-1009', 'Mochila', 1, 95.00, 95.00);

-- Items para order_id 8
INSERT INTO order_items (orderid, product_sku, product_name, quantity, price, subtotal)
VALUES
(8, 'SKU-1010', 'Refrigeradora', 1, 450.00, 450.00);

-- Items para order_id 9
INSERT INTO order_items (orderid, product_sku, product_name, quantity, price, subtotal)
VALUES
(9, 'SKU-1011', 'Escritorio de Oficina', 1, 900.00, 900.00);

-- Items para order_id 10
INSERT INTO order_items (orderid, product_sku, product_name, quantity, price, subtotal)
VALUES
(10, 'SKU-1012', 'Silla Gamer', 1, 175.00, 175.00);

-- Items para order_id 11
INSERT INTO order_items (orderid, product_sku, product_name, quantity, price, subtotal)
VALUES
(11, 'SKU-1013', 'Televisor 55\"', 1, 1600.00, 1600.00);

-- Items para order_id 12
INSERT INTO order_items (orderid, product_sku, product_name, quantity, price, subtotal)
VALUES
(12, 'SKU-1014', 'Horno Microondas', 1, 130.00, 130.00);
