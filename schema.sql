-- NetOps Desk MySQL 8.x Schema Reference
-- Run this script in MySQL if you prefer manual schema provisioning
-- instead of `flask --app run.py init-db`.

CREATE DATABASE IF NOT EXISTS netops_desk
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE netops_desk;

CREATE TABLE IF NOT EXISTS devices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    ip_address VARCHAR(45) NOT NULL UNIQUE,
    device_type VARCHAR(50) NOT NULL,
    location VARCHAR(120) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ONLINE',
    simulated_latency_ms FLOAT NULL DEFAULT 12.5,
    simulated_uptime_pct FLOAT NOT NULL DEFAULT 99.95,
    last_checked DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT ck_devices_status CHECK (status IN ('ONLINE', 'OFFLINE', 'WARNING')),
    INDEX ix_devices_status (status)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS incidents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    description TEXT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    resolved_at DATETIME NULL,
    CONSTRAINT fk_incidents_device
        FOREIGN KEY (device_id) REFERENCES devices(id)
        ON DELETE CASCADE,
    CONSTRAINT ck_incidents_priority CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    CONSTRAINT ck_incidents_status CHECK (status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED')),
    INDEX ix_incidents_device_id (device_id),
    INDEX ix_incidents_priority (priority),
    INDEX ix_incidents_status (status)
) ENGINE=InnoDB;
