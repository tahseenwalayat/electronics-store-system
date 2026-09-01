-- Migration 001: Add model column to products table
ALTER TABLE products ADD COLUMN model TEXT;
