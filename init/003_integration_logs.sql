CREATE TABLE IF NOT EXISTS integration_logs (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  order_id BIGINT NOT NULL,
  system VARCHAR(32) NOT NULL,      -- e.g. 'mcp','odoo','zoho'
  status VARCHAR(16) NOT NULL,      -- 'info','sent','error'
  message TEXT,
  payload_preview JSON NULL,
  ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
