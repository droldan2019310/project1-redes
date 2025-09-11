CREATE TABLE IF NOT EXISTS mcp_sessions (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(255) DEFAULT NULL,
  started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mcp_messages (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  session_id BIGINT NOT NULL,
  role ENUM('user','assistant','system','tool') NOT NULL,
  content JSON NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES mcp_sessions(id) ON DELETE CASCADE
);


CREATE INDEX idx_mcp_messages_session_time ON mcp_messages(session_id, created_at);
