/**
 * KeyphraseClustersView.jsx - View pura para seleção de clusters MVVM
 * UI pura sem lógica de negócio, recebe tudo via props do ViewModel
 * PADRÃO REACTPY: Segue exato o componente backend/components/keyphrase_clusters.py
 */
import React from 'react';
import { 
  Box,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  Divider,
  Chip,
  Paper
} from '@mui/material';
import { MainLayout } from '../layouts/index.js';
import { Button, AdjudicatorClusters, AdjudicatorAgreementPanel } from '../components/index.js';
import { ClusterSorting, ClusterSortingLabels } from '../../shared/enums/ClusterSorting.js';

/**
 * KeyphraseClustersView - Componente View puro seguindo padrão MVVM
 * 
 * ESTRUTURA REACTPY:
 * - order_select: Select para ordenação (5 opções do ClusterSorting)
 * - cluster_select (CS): Select 0/1 para seleção do cluster
 * - keyphrase_select (S1/S2): Select para keyphrases dentro do cluster
 * - cluster_chips: Chips coloridos baseados no estado de seleção
 * 
 * CORES DOS CHIPS (ReactPy get_chip_color):
 * - success (verde): cluster selecionado (CS=1) + keyphrase selecionada (S1 ou S2)
 * - error (vermelho): cluster rejeitado (CS=0) + keyphrase selecionada
 * - warning (amarelo): cluster indefinido (CS=-1) + keyphrase selecionada
 * - default (cinza): keyphrase não selecionada
 */
const KeyphraseClustersView = ({
  // ============================================================================
  // ESTADO DO VIEWMODEL
  // ============================================================================
  
  // Dados principais
  clusters = {},
  clusterOrder = [], // NOVO: Array com ordem correta dos cluster IDs
  selectedClusters = {},
  selectedKeyphrases = {},
  clustersInfo = {},
  adjudicatorData = {},
  
  // Estado de ordenação
  currentSorting,
  sortingStats = {},
  availableSortings = [],
  
  // Estado de loading e erro
  loading = false,
  saving = false,
  error = null,
  
  // Dados do contexto
  user,
  currentTopic,
  username,
  topicName,
  
  // Validações
  canProceed = false,
  hasClusters = false,
  isWorking = false,
  isAdjudicatorMode = false,
  
  // ============================================================================
  // AÇÕES DO VIEWMODEL
  // ============================================================================
  
  // Handlers principais - PADRÃO REACTPY: recebem strings "id,value"
  onClusterOrderChange,          // (value: string) => void - Muda ordenação (5 tipos)
  onAdjudicatorAction,           // ({clusterId, keyphrase, newAction}) => void - Ação de adjudicação
  onClusterSelectionChange,      // (value: string) => void - "clusterId,selection" (0/1)
  onKeyphrase1SelectionChange,   // (value: string) => void - "clusterId,keyphraseId"
  onKeyphrase2SelectionChange,   // (value: string) => void - "clusterId,keyphraseId"
  onSortingChange,               // (sorting: ClusterSorting) => void - Muda tipo de ordenação
  
  // Utilitários
  getKeyphraseChipColor,         // (clusterId, keyphraseId) => color
  isClusterDisabled,             // (clusterId) => boolean
  getSelectedCluster,            // (clusterId) => "0"|"1"|"-1"
  getSelectedKeyphrase,          // (clusterId, order) => keyphraseId
  extractKeyphraseId,            // (keyphraseStr) => id
  refreshData,                   // () => void
  
  // Navegação
  onNext,
  onBack,
  
  // Props opcionais
  title = "Keyphrase Clusters",
  embedded = false,              // Para usar como sub-componente
  showControls = true            // Mostrar controles de ordenação
}) => {
  // ============================================================================
  // ESTATÍSTICAS
  // ============================================================================
  
  const totalClusters = Object.keys(clusters).length;
  const selectedCount = Object.values(selectedClusters).filter(value => value === "1").length;
  const progressPercent = totalClusters > 0 ? Math.round((selectedCount / totalClusters) * 100) : 0;

  // ============================================================================
  // RENDERIZAÇÃO DE CLUSTERS - PADRÃO REACTPY cluster_chips_control
  // ============================================================================
  
  /**
   * Renderiza um único cluster seguindo padrão ReactPy:
   * - Controles: CS (Cluster Selection 0/1), S1 (Keyphrase 1), S2 (Keyphrase 2)
   * - Chips: Coloridos baseados no estado (get_chip_color)
   * - Borda: Verde (selecionado), Vermelho (rejeitado), Amarelo (indefinido)
   */
  const renderCluster = (clusterId, clusterData) => {
    // Extrair descrição e keyphrases do cluster
    const clusterDescription = Array.isArray(clusterData) && clusterData.length > 0 
      ? (typeof clusterData[0] === 'string' ? clusterData[0] : JSON.stringify(clusterData[0]))
      : `Cluster ${clusterId}`;
    
    const keyphrases = Array.isArray(clusterData) && clusterData.length > 1 
      ? clusterData[1] 
      : [];

    // Obter estado atual
    const clusterSelection = getSelectedCluster ? getSelectedCluster(clusterId) : "0";
    const selected1 = getSelectedKeyphrase ? getSelectedKeyphrase(clusterId, 1) : "0";
    const selected2 = getSelectedKeyphrase ? getSelectedKeyphrase(clusterId, 2) : "0";
    const disabled = isClusterDisabled ? isClusterDisabled(clusterId) : false;

    // Determinar cor da borda baseado no estado
    let borderColor = "grey.300"; // Padrão
    if (clusterSelection === "1") borderColor = "success.main"; // Verde
    else if (clusterSelection === "0") borderColor = "error.main"; // Vermelho
    else if (clusterSelection === "-1") borderColor = "warning.main"; // Amarelo

    return (
      <Paper
        key={clusterId}
        elevation={2}
        sx={{ 
          display: 'flex', 
          flexDirection: 'row',
          mb: 2,
          p: 2,
          border: 2,
          borderColor,
          transition: 'border-color 0.3s',
          opacity: disabled ? 0.6 : 1
        }}
      >
        {/* CONTROLES - PADRÃO REACTPY: cluster_select, keyphrase_select */}
        <Box sx={{ 
          display: 'flex', 
          flexDirection: 'column',
          gap: 1,
          mr: 3,
          minWidth: 80
        }}>
          {/* CS - Cluster Selection (0/1) */}
          <FormControl size="small" fullWidth>
            <InputLabel id={`cs-label-${clusterId}`}>CS</InputLabel>
            <Select
              labelId={`cs-label-${clusterId}`}
              value={`${clusterId},${clusterSelection}`}
              onChange={(e) => onClusterSelectionChange && onClusterSelectionChange(e.target.value)}
              label="CS"
              disabled={disabled}
            >
              <MenuItem value={`${clusterId},0`}>0</MenuItem>
              <MenuItem value={`${clusterId},1`}>1</MenuItem>
            </Select>
          </FormControl>

          {/* S1 - Keyphrase Selection 1 */}
          <FormControl size="small" fullWidth>
            <InputLabel id={`s1-label-${clusterId}`}>S1</InputLabel>
            <Select
              labelId={`s1-label-${clusterId}`}
              value={`${clusterId},${selected1}`}
              onChange={(e) => onKeyphrase1SelectionChange && onKeyphrase1SelectionChange(e.target.value)}
              label="S1"
              disabled={disabled}
            >
              <MenuItem value={`${clusterId},0`}>0</MenuItem>
              {Array.isArray(keyphrases) && keyphrases.map((keyphrase, idx) => {
                if (!keyphrase) return null;
                const keyphraseStr = typeof keyphrase === 'string' ? keyphrase : String(keyphrase);
                const kpId = extractKeyphraseId ? extractKeyphraseId(keyphraseStr) : String(idx + 1);
                return (
                  <MenuItem key={kpId || idx} value={`${clusterId},${kpId}`}>
                    {kpId}
                  </MenuItem>
                );
              })}
            </Select>
          </FormControl>

          {/* S2 - Keyphrase Selection 2 */}
          <FormControl size="small" fullWidth>
            <InputLabel id={`s2-label-${clusterId}`}>S2</InputLabel>
            <Select
              labelId={`s2-label-${clusterId}`}
              value={`${clusterId},${selected2}`}
              onChange={(e) => onKeyphrase2SelectionChange && onKeyphrase2SelectionChange(e.target.value)}
              label="S2"
              disabled={disabled}
            >
              <MenuItem value={`${clusterId},0`}>0</MenuItem>
              {Array.isArray(keyphrases) && keyphrases.map((keyphrase, idx) => {
                if (!keyphrase) return null;
                const keyphraseStr = typeof keyphrase === 'string' ? keyphrase : String(keyphrase);
                const kpId = extractKeyphraseId ? extractKeyphraseId(keyphraseStr) : String(idx + 1);
                return (
                  <MenuItem key={kpId || idx} value={`${clusterId},${kpId}`}>
                    {kpId}
                  </MenuItem>
                );
              })}
            </Select>
          </FormControl>
        </Box>

        {/* CHIPS - PADRÃO REACTPY: cluster_chips */}
        <Box sx={{ flex: 1 }}>
          <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 600, mb: 1.5 }}>
            {clusterDescription}
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
            {Array.isArray(keyphrases) && keyphrases.length > 0 ? (
              keyphrases.map((keyphrase, idx) => {
                if (!keyphrase) return null;
                
                const keyphraseStr = typeof keyphrase === 'string' ? keyphrase : String(keyphrase);
                const kpId = extractKeyphraseId ? extractKeyphraseId(keyphraseStr) : String(idx + 1);
                
                // PADRÃO REACTPY: get_chip_color
                const chipColor = getKeyphraseChipColor 
                  ? getKeyphraseChipColor(clusterId, kpId) 
                  : "default";

                return (
                  <Chip
                    key={idx}
                    label={keyphraseStr}
                    variant="filled"
                    color={chipColor}
                    size="small"
                    sx={{ 
                      m: 0.25, 
                      fontSize: '0.75rem',
                      fontWeight: chipColor !== "default" ? 600 : 400
                    }}
                  />
                );
              })
            ) : (
              <Typography variant="body2" color="text.secondary">
                Nenhuma keyphrase disponível
              </Typography>
            )}
          </Box>
        </Box>
      </Paper>
    );
  };

  /**
   * Renderiza lista de clusters ordenados
   */
  const renderClusters = () => {
    // MODO ADJUDICATOR: renderizar chips de adjudicação
    // (fiel ao adjudicator_clusters.py) com os dados dos anotadores.
    // Verificar ANTES do hasClusters: no modo adjudicator os dados vêm
    // de adjudicatorData, não do estado clusters (que fica vazio para
    // a ordenação clues_from_other_annotators).
    if (isAdjudicatorMode && adjudicatorData &&
        adjudicatorData.union &&
        Object.keys(adjudicatorData.union).length > 0) {
      return (
        <>
          <AdjudicatorAgreementPanel agreement={adjudicatorData.agreement} />
          <AdjudicatorClusters
            clustersAnnotationData={adjudicatorData}
            onAdjudicatorAction={onAdjudicatorAction}
          />
        </>
      );
    }

    if (!hasClusters) {
      return (
        <Alert severity="info">
          Nenhum cluster disponível.
        </Alert>
      );
    }

    // IMPORTANTE: Usar clusterOrder (array de IDs na ordem correta do backend)
    // Em vez de Object.entries que reordena numericamente
    const clusterEntries = clusterOrder
      .filter(clusterId => clusters[clusterId] !== null && clusters[clusterId] !== undefined)
      .map(clusterId => [String(clusterId), clusters[clusterId]]);

    return (
      <Box sx={{ display: 'flex', flexDirection: 'column' }}>
        {clusterEntries.map(([clusterId, clusterData]) => 
          renderCluster(clusterId, clusterData)
        )}
      </Box>
    );
  };

  // ============================================================================
  // RENDERIZAÇÃO PRINCIPAL
  // ============================================================================

  /**
   * Renderiza conteúdo baseado no estado
   */
  const renderContent = () => {
    // Estado de loading
    if (loading) {
      return (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <CircularProgress size={40} />
          <Typography variant="body1" sx={{ mt: 2 }}>
            Carregando clusters...
          </Typography>
        </Box>
      );
    }

    // Estado de erro
    if (error) {
      return (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      );
    }

    return (
      <>
        {/* INSTRUÇÕES */}
        <Alert severity="info" sx={{ mb: 3 }}>
          <Typography variant="body2" paragraph>
            <strong>Instruções:</strong>
          </Typography>
          <Typography variant="body2" component="div">
            • <strong>Order by:</strong> Escolha entre as 5 formas de ordenação dos clusters
            <br />
            • <strong>CS (Cluster Selection):</strong> 1 = selecionado, 0 = rejeitado
            <br />
            • <strong>S1/S2:</strong> Selecione até 2 keyphrases principais de cada cluster
            <br />
            • <strong>Cores dos chips:</strong> Verde (cluster selecionado), Vermelho (rejeitado), Cinza (não selecionado)
          </Typography>
        </Alert>

        {/* ESTATÍSTICAS */}
        <Paper sx={{ mb: 3, p: 2, backgroundColor: 'grey.50' }} elevation={1}>
          <Typography variant="h6" gutterBottom>
            Progresso da Seleção
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="body1">
              <strong>{selectedCount}</strong> de <strong>{totalClusters}</strong> clusters selecionados
            </Typography>
            <Typography variant="body2" color="text.secondary">
              ({progressPercent}%)
            </Typography>
          </Box>
          
          {/* Info adicional da ordenação */}
          {sortingStats && sortingStats.message && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              {sortingStats.message}
            </Typography>
          )}
        </Paper>

        {/* CONTROLE DE ORDENAÇÃO - PADRÃO REACTPY: order_select com 5 opções */}
        {showControls && (
          <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
            <FormControl sx={{ minWidth: 300 }}>
              <InputLabel id="order-by-label">Order by</InputLabel>
              <Select
                labelId="order-by-label"
                value={currentSorting || ClusterSorting.NUMERICAL}
                onChange={(e) => onClusterOrderChange && onClusterOrderChange(e.target.value)}
                label="Order by"
                disabled={isWorking}
              >
                {availableSortings.map((sorting) => (
                  <MenuItem key={sorting} value={sorting}>
                    {ClusterSortingLabels[sorting] || sorting}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Info da ordenação atual */}
            {clustersInfo && clustersInfo.description && (
              <Typography variant="body2" color="text.secondary">
                {clustersInfo.description}
              </Typography>
            )}
            
            {saving && (
              <CircularProgress size={20} />
            )}
          </Box>
        )}

        <Divider sx={{ mb: 3 }} />

        {/* LISTA DE CLUSTERS */}
        {renderClusters()}

        {/* NAVEGAÇÃO */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 4, pt: 2, borderTop: 1, borderColor: 'divider' }}>
          <Button 
            variant="outlined" 
            onClick={onBack}
            disabled={isWorking}
          >
            ← Voltar: Clustering
          </Button>
          <Button 
            variant="contained" 
            onClick={onNext}
            disabled={!canProceed || isWorking}
          >
            Próximo: Curação Final →
            {selectedCount > 0 && ` (${selectedCount} selecionados)`}
          </Button>
        </Box>
      </>
    );
  };

  // ============================================================================
  // MODO EMBEDDED - Para uso como sub-componente
  // ============================================================================

  if (embedded) {
    return (
      <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        {/* Título */}
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
          {title}
        </Typography>

        {/* Controles inline */}
        <Box sx={{ 
          display: 'flex', 
          flexDirection: 'row',
          alignItems: 'center',
          gap: 2,
          mb: 2
        }}>
          {/* Order by Select */}
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>Order by</InputLabel>
            <Select
              value={currentSorting || ClusterSorting.NUMERICAL}
              onChange={(e) => onClusterOrderChange && onClusterOrderChange(e.target.value)}
              label="Order by"
            >
              {availableSortings.map((sorting) => (
                <MenuItem key={sorting} value={sorting}>
                  {ClusterSortingLabels[sorting] || sorting}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          
          {/* Info */}
          {clustersInfo && clustersInfo.description && (
            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
              {clustersInfo.description}
            </Typography>
          )}
        </Box>

        {/* Lista de Clusters */}
        <Box sx={{ 
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'auto'
        }}>
          {loading ? (
            <Box sx={{ textAlign: 'center', py: 2 }}>
              <CircularProgress size={24} />
              <Typography variant="body2" sx={{ mt: 1 }}>
                Carregando...
              </Typography>
            </Box>
          ) : error ? (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          ) : (
            renderClusters()
          )}
        </Box>
      </Box>
    );
  }

  // ============================================================================
  // MODO STANDALONE - Renderização completa com layout
  // ============================================================================

  return (
    <MainLayout
      title={title}
      user={user}
      currentTopic={topicName || currentTopic?.name || currentTopic?.id}
      currentStep="Seleção de Clusters"
      breadcrumbs={[
        { label: 'Home', href: '/' },
        { label: 'Tópicos', href: '/topics' },
        { label: topicName || currentTopic?.name || 'Tópico', href: '/topics' },
        { label: 'Clustering', href: '/clustering' },
        { label: 'Seleção de Clusters' }
      ]}
    >
      {renderContent()}
    </MainLayout>
  );
};

export default KeyphraseClustersView;