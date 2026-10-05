-- ==========================================================================
-- FinGuard Bank — MySQL Schema
-- ==========================================================================
-- NOTE: The FastAPI backend auto-creates these tables on startup via
-- SQLAlchemy (Base.metadata.create_all). This file is provided so you can
-- also inspect/run the schema manually, e.g. in phpMyAdmin/XAMPP, or set
-- up the database ahead of time.
--
-- Run:  mysql -u root -p < database/schema.sql
-- ==========================================================================

CREATE DATABASE IF NOT EXISTS finguard_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE finguard_db;

-- --------------------------------------------------------------------------
-- users
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id CHAR(36) PRIMARY KEY,
  full_name VARCHAR(150) NOT NULL,
  email VARCHAR(150) NOT NULL UNIQUE,
  phone VARCHAR(20) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  status ENUM('active','suspended','locked') NOT NULL DEFAULT 'active',
  bvn_last4 VARCHAR(4),
  home_city VARCHAR(100),
  home_country VARCHAR(100) DEFAULT 'Nigeria',
  face_descriptor JSON,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_users_email (email),
  INDEX idx_users_phone (phone)
) ENGINE=InnoDB;

-- --------------------------------------------------------------------------
-- admin_users
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_users (
  id CHAR(36) PRIMARY KEY,
  full_name VARCHAR(150) NOT NULL,
  email VARCHAR(150) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('fraud_analyst','super_admin') NOT NULL DEFAULT 'fraud_analyst',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- --------------------------------------------------------------------------
-- accounts
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS accounts (
  id CHAR(36) PRIMARY KEY,
  user_id CHAR(36) NOT NULL UNIQUE,
  account_number VARCHAR(10) NOT NULL UNIQUE,
  bank_name VARCHAR(100) DEFAULT 'FinGuard Bank',
  balance DECIMAL(18,2) DEFAULT 0,
  currency VARCHAR(3) DEFAULT 'NGN',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_accounts_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_accounts_number (account_number)
) ENGINE=InnoDB;

-- --------------------------------------------------------------------------
-- devices
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS devices (
  id CHAR(36) PRIMARY KEY,
  user_id CHAR(36) NOT NULL,
  device_fingerprint VARCHAR(255) NOT NULL,
  device_name VARCHAR(150),
  browser VARCHAR(100),
  operating_system VARCHAR(100),
  is_trusted BOOLEAN DEFAULT FALSE,
  first_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  times_used INT DEFAULT 1,
  CONSTRAINT fk_devices_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_devices_fingerprint (device_fingerprint)
) ENGINE=InnoDB;

-- --------------------------------------------------------------------------
-- login_sessions
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS login_sessions (
  id CHAR(36) PRIMARY KEY,
  user_id CHAR(36) NOT NULL,
  device_fingerprint VARCHAR(255),
  ip_address VARCHAR(45),
  city VARCHAR(100),
  country VARCHAR(100),
  login_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  logout_at DATETIME,
  success BOOLEAN DEFAULT TRUE,
  CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- --------------------------------------------------------------------------
-- user_behavior_profiles
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_behavior_profiles (
  id CHAR(36) PRIMARY KEY,
  user_id CHAR(36) NOT NULL UNIQUE,
  avg_transaction_amount DECIMAL(18,2) DEFAULT 0,
  max_transaction_amount DECIMAL(18,2) DEFAULT 0,
  std_dev_amount DECIMAL(18,2) DEFAULT 0,
  typical_min_amount DECIMAL(18,2) DEFAULT 0,
  typical_max_amount DECIMAL(18,2) DEFAULT 0,
  typical_start_hour INT DEFAULT 8,
  typical_end_hour INT DEFAULT 21,
  common_recipients JSON,
  common_cities JSON,
  home_country VARCHAR(100) DEFAULT 'Nigeria',
  total_transactions INT DEFAULT 0,
  transactions_last_24h INT DEFAULT 0,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_profile_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- --------------------------------------------------------------------------
-- transactions
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
  id CHAR(36) PRIMARY KEY,
  reference VARCHAR(30) NOT NULL UNIQUE,
  sender_id CHAR(36) NOT NULL,
  sender_account_number VARCHAR(10) NOT NULL,
  recipient_account_number VARCHAR(10) NOT NULL,
  recipient_name VARCHAR(150),
  recipient_bank VARCHAR(100),
  amount DECIMAL(18,2) NOT NULL,
  transaction_type ENUM('transfer','bill_payment','airtime','withdrawal') DEFAULT 'transfer',
  narration VARCHAR(255),
  device_fingerprint VARCHAR(255),
  browser VARCHAR(100),
  operating_system VARCHAR(100),
  ip_address VARCHAR(45),
  city VARCHAR(100),
  country VARCHAR(100),
  risk_level ENUM('SAFE','CAUTION','VERIFY','HIGH_RISK','CRITICAL'),
  risk_score DECIMAL(5,2),
  risk_factors JSON,
  fraud_rule_version VARCHAR(20),
  status ENUM('pending','awaiting_otp','awaiting_verification','approved','completed','rejected','blocked') NOT NULL DEFAULT 'pending',
  investigation_status ENUM('none','open','reviewing','confirmed_fraud','confirmed_legitimate','closed') DEFAULT 'none',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  completed_at DATETIME,
  CONSTRAINT fk_txn_sender FOREIGN KEY (sender_id) REFERENCES users(id),
  INDEX idx_txn_sender (sender_id),
  INDEX idx_txn_created (created_at),
  INDEX idx_txn_reference (reference),
  INDEX idx_txn_risk (risk_level)
) ENGINE=InnoDB;

-- --------------------------------------------------------------------------
-- fraud_events
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fraud_events (
  id CHAR(36) PRIMARY KEY,
  transaction_id CHAR(36) NOT NULL,
  user_id CHAR(36) NOT NULL,
  risk_level VARCHAR(20) NOT NULL,
  risk_score DECIMAL(5,2),
  risk_factors JSON NOT NULL,
  fraud_rule_version VARCHAR(20),
  status ENUM('open','reviewing','resolved_fraud','resolved_legitimate') DEFAULT 'open',
  reviewed_by_admin_id CHAR(36),
  admin_notes TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  resolved_at DATETIME,
  CONSTRAINT fk_event_txn FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
  CONSTRAINT fk_event_user FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT fk_event_admin FOREIGN KEY (reviewed_by_admin_id) REFERENCES admin_users(id),
  INDEX idx_events_status (status),
  INDEX idx_events_created (created_at)
) ENGINE=InnoDB;

-- --------------------------------------------------------------------------
-- fraud_rules
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fraud_rules (
  id CHAR(36) PRIMARY KEY,
  rule_key VARCHAR(100) NOT NULL UNIQUE,
  description VARCHAR(255) NOT NULL,
  weight DECIMAL(5,2) NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  version VARCHAR(20) DEFAULT '1.0.0',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- --------------------------------------------------------------------------
-- verification_attempts
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS verification_attempts (
  id CHAR(36) PRIMARY KEY,
  transaction_id CHAR(36) NOT NULL,
  method ENUM('otp','facial_simulation') NOT NULL,
  code_hash VARCHAR(255),
  result ENUM('pending','success','failed','expired') DEFAULT 'pending',
  attempts_made VARCHAR(5) DEFAULT '0',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  expires_at DATETIME,
  verified_at DATETIME,
  CONSTRAINT fk_verify_txn FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- --------------------------------------------------------------------------
-- audit_logs
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
  id CHAR(36) PRIMARY KEY,
  actor_type VARCHAR(20) NOT NULL,
  actor_id CHAR(36),
  action VARCHAR(100) NOT NULL,
  entity_type VARCHAR(50),
  entity_id CHAR(36),
  details JSON,
  ip_address VARCHAR(45),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_audit_created (created_at),
  INDEX idx_audit_action (action)
) ENGINE=InnoDB;

-- --------------------------------------------------------------------------
-- beneficiary_risk_profiles  (FinShield v2 -- Beneficiary Risk Analysis)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS beneficiary_risk_profiles (
  id CHAR(36) PRIMARY KEY,
  account_number VARCHAR(10) NOT NULL UNIQUE,
  risk_category ENUM('TRUSTED','WATCHLISTED','HIGH_RISK') NOT NULL,
  tags JSON,
  reason TEXT,
  fraud_report_count INT DEFAULT 0,
  complaint_count INT DEFAULT 0,
  added_by_admin_id CHAR(36),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_beneficiary_admin FOREIGN KEY (added_by_admin_id) REFERENCES admin_users(id),
  INDEX idx_beneficiary_account (account_number)
) ENGINE=InnoDB;
