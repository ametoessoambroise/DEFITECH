-- Schema SQL pour les tables de dataset DEFITECH AI
-- Généré à partir des modèles SQLAlchemy

-- ============================================
-- TABLE DATASET (nouvelle table principale)
-- ============================================

CREATE TABLE IF NOT EXISTS dataset (
    -- Clé primaire
    id SERIAL PRIMARY KEY,
    
    -- Champs principaux pour l'entraînement
    input_text TEXT NOT NULL COMMENT 'Requête de l''utilisateur',
    output_text TEXT NOT NULL COMMENT 'Réponse de l''IA',
    
    -- Métadonnées temporelles
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Métadonnées optionnelles pour l'analyse
    user_role VARCHAR(20) COMMENT 'Rôle de l''utilisateur (etudiant, enseignant, admin)',
    conversation_id INTEGER COMMENT 'ID de la conversation d''origine',
    tokens_used INTEGER DEFAULT 0 COMMENT 'Nombre de tokens utilisés par la réponse IA'
);

-- Contraintes pour la table dataset
ALTER TABLE dataset 
ADD CONSTRAINT chk_dataset_role 
CHECK (user_role IN ('etudiant', 'enseignant', 'admin', NULL));

-- Index pour optimiser les requêtes sur le dataset
CREATE INDEX idx_dataset_created_at ON dataset(created_at);
CREATE INDEX idx_dataset_user_role ON dataset(user_role);
CREATE INDEX idx_dataset_conversation_id ON dataset(conversation_id);

-- ============================================
-- TABLES EXISTANTES (pour référence)
-- ============================================

-- Table AIConversation (déjà existante)
CREATE TABLE IF NOT EXISTS ai_conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) DEFAULT 'Nouvelle conversation',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    user_role VARCHAR(20) NOT NULL,
    context_data JSON DEFAULT '{}',
    
    CONSTRAINT chk_conversation_role 
    CHECK (user_role IN ('etudiant', 'enseignant', 'admin'))
);

-- Index pour AIConversation
CREATE INDEX idx_ai_conversations_user_id ON ai_conversations(user_id);
CREATE INDEX idx_ai_conversations_created_at ON ai_conversations(created_at);
CREATE INDEX idx_ai_conversations_is_active ON ai_conversations(is_active);

-- Table AIMessage (déjà existante)
CREATE TABLE IF NOT EXISTS ai_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
    message_type VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    extra_data JSON DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_order INTEGER NOT NULL,
    
    CONSTRAINT chk_message_type 
    CHECK (message_type IN ('user', 'assistant', 'system'))
);

-- Index pour AIMessage
CREATE INDEX idx_ai_messages_conversation_id ON ai_messages(conversation_id);
CREATE INDEX idx_ai_messages_created_at ON ai_messages(created_at);
CREATE INDEX idx_ai_messages_message_order ON ai_messages(message_order);

-- ============================================
-- VUES UTILES
-- ============================================

-- Vue pour les statistiques du dataset
CREATE VIEW v_dataset_stats AS
SELECT 
    COUNT(*) as total_entries,
    COUNT(DISTINCT conversation_id) as unique_conversations,
    COUNT(DISTINCT user_role) as unique_roles,
    AVG(LENGTH(input_text)) as avg_input_length,
    AVG(LENGTH(output_text)) as avg_output_length,
    SUM(tokens_used) as total_tokens,
    MIN(created_at) as earliest_entry,
    MAX(created_at) as latest_entry
FROM dataset;

-- Vue pour les entrées par rôle
CREATE VIEW v_dataset_by_role AS
SELECT 
    user_role,
    COUNT(*) as entry_count,
    AVG(LENGTH(input_text)) as avg_input_length,
    AVG(LENGTH(output_text)) as avg_output_length,
    SUM(tokens_used) as total_tokens
FROM dataset 
WHERE user_role IS NOT NULL
GROUP BY user_role
ORDER BY entry_count DESC;

-- Vue pour les conversations complètes (jointure avec AIConversation)
CREATE VIEW v_dataset_with_conversations AS
SELECT 
    d.id,
    d.input_text,
    d.output_text,
    d.created_at,
    d.user_role,
    d.conversation_id,
    d.tokens_used,
    ac.title as conversation_title,
    ac.user_id as conversation_user_id
FROM dataset d
LEFT JOIN ai_conversations ac ON d.conversation_id = ac.id;

-- ============================================
-- TRIGGERS OPTIONNELS
-- ============================================

-- Trigger pour mettre à jour les timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Appliquer le trigger sur AIConversation
CREATE TRIGGER update_ai_conversations_updated_at 
    BEFORE UPDATE ON ai_conversations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- SÉQUENCES (gérées automatiquement par SERIAL)
-- ============================================

-- Les séquences sont créées automatiquement pour les champs SERIAL:
-- - dataset_id_seq
-- - ai_conversations_id_seq  
-- - ai_messages_id_seq

-- ============================================
-- DROITS ET PERMISSIONS
-- ============================================

-- Exemple de permissions (à adapter selon votre configuration)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON dataset TO defitech_app;
-- GRANT SELECT ON v_dataset_stats TO defitech_readonly;
-- GRANT SELECT ON v_dataset_by_role TO defitech_readonly;
-- GRANT SELECT ON v_dataset_with_conversations TO defitech_readonly;

-- ============================================
-- EXEMPLES DE REQUÊTES UTILES
-- ============================================

-- Nombre total d'entrées dans le dataset
-- SELECT COUNT(*) FROM dataset;

-- Entrées par rôle utilisateur
-- SELECT user_role, COUNT(*) FROM dataset GROUP BY user_role;

-- Entrées récentes (derniers 7 jours)
-- SELECT * FROM dataset WHERE created_at >= CURRENT_DATE - INTERVAL '7 days';

-- Entrées les plus longues
-- SELECT input_text, LENGTH(input_text) as input_length FROM dataset ORDER BY input_length DESC LIMIT 10;

-- Statistiques complètes
-- SELECT * FROM v_dataset_stats;

-- Export pour l'entraînement (format JSON)
-- SELECT json_agg(
--     json_build_object(
--         'input', input_text,
--         'output', output_text
--     )
-- ) FROM dataset ORDER BY created_at;
