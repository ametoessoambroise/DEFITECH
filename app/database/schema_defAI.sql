-- ========================================
-- SCHÉMA POSTGRESQL POUR L'ASSISTANT IA defAI
-- ========================================

-- Table pour stocker les conversations IA
CREATE TABLE IF NOT EXISTS ai_conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) DEFAULT 'Nouvelle conversation',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    user_role VARCHAR(20) NOT NULL CHECK (user_role IN ('student', 'teacher', 'admin')),
    context_data JSONB DEFAULT '{}' -- Données contextuelles au début de la conversation
);

-- Table pour stocker les messages des conversations
CREATE TABLE IF NOT EXISTS ai_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
    message_type VARCHAR(20) NOT NULL CHECK (message_type IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    extra_data JSONB DEFAULT '{}', -- Données supplémentaires (tokens, temps de réponse, etc.)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_order INTEGER NOT NULL -- Ordre dans la conversation
);

-- Table pour les requêtes internes de l'IA
CREATE TABLE IF NOT EXISTS ai_internal_requests (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
    message_id INTEGER REFERENCES ai_messages(id) ON DELETE CASCADE,
    request_type VARCHAR(50) NOT NULL, -- Type de requête (get_student_notes, get_class_stats, etc.)
    endpoint VARCHAR(255) NOT NULL, -- Endpoint appelé
    request_data JSONB DEFAULT '{}', -- Données envoyées
    response_data JSONB DEFAULT '{}', -- Réponse reçue
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'success', 'failed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Table pour le contexte utilisateur par session
CREATE TABLE IF NOT EXISTS ai_user_context (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(255) NOT NULL,
    context_data JSONB NOT NULL DEFAULT '{}',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '24 hours'),
    UNIQUE(user_id, session_id)
);

-- Index pour optimiser les performances
CREATE INDEX IF NOT EXISTS idx_ai_conversations_user_id ON ai_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_conversations_updated_at ON ai_conversations(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_messages_conversation_id ON ai_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_ai_messages_order ON ai_messages(conversation_id, message_order);
CREATE INDEX IF NOT EXISTS idx_ai_internal_requests_conversation_id ON ai_internal_requests(conversation_id);
CREATE INDEX IF NOT EXISTS idx_ai_user_context_user_session ON ai_user_context(user_id, session_id);
CREATE INDEX IF NOT EXISTS idx_ai_user_context_expires_at ON ai_user_context(expires_at);

-- Trigger pour mettre à jour updated_at des conversations
DROP TRIGGER IF EXISTS trigger_update_conversation_updated_at ON ai_messages;
DROP FUNCTION IF EXISTS update_conversation_updated_at();

CREATE OR REPLACE FUNCTION update_conversation_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE ai_conversations 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_conversation_updated_at
    AFTER INSERT ON ai_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_updated_at();

-- Trigger pour nettoyer les contextes expirés
CREATE OR REPLACE FUNCTION cleanup_expired_contexts()
RETURNS void AS $$
BEGIN
    DELETE FROM ai_user_context WHERE expires_at < CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Commentaires sur les tables
COMMENT ON TABLE ai_conversations IS 'Conversations entre utilisateurs et l''IA assistant';
COMMENT ON TABLE ai_messages IS 'Messages échangés dans les conversations IA';
COMMENT ON TABLE ai_internal_requests IS 'Requêtes internes effectuées par l''IA pour obtenir des données';
COMMENT ON TABLE ai_user_context IS 'Contexte utilisateur temporaire pour les sessions IA';
