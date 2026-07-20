-- Migration: Add user_id to contact_messages table
-- Date: 2025-07-11
-- Description: Associate contact messages with logged-in users

-- Add user_id column
ALTER TABLE contact_messages
ADD COLUMN user_id VARCHAR(50) NULL;

-- Add foreign key constraint
ALTER TABLE contact_messages
ADD CONSTRAINT fk_contact_messages_user_id
FOREIGN KEY (user_id) REFERENCES users(user_id)
ON DELETE CASCADE;

-- Create index for performance
CREATE INDEX idx_contact_messages_user_id ON contact_messages(user_id);

-- Update existing messages to associate with users based on email match (optional)
-- This is commented out by default, uncomment if you want to retroactively associate messages
-- UPDATE contact_messages cm
-- SET user_id = u.user_id
-- FROM users u
-- WHERE cm.email = u.email
-- AND cm.user_id IS NULL;