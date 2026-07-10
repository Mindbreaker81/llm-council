import pdfMake from 'pdfmake/build/pdfmake';
import pdfFonts from 'pdfmake/build/vfs_fonts';
import { marked } from 'marked';

// Configure pdfmake with fonts (vfs_fonts includes Roboto by default)
if (pdfFonts && pdfFonts.pdfMake && pdfFonts.pdfMake.vfs) {
  pdfMake.vfs = pdfFonts.pdfMake.vfs;
} else if (pdfFonts) {
  pdfMake.vfs = pdfFonts;
}

// Define available fonts (Roboto comes with vfs_fonts)
// Note: Standard PDF fonts (Courier, Helvetica, Times) are NOT available in the browser, only in Node.js.
pdfMake.fonts = {
  Roboto: {
    normal: 'Roboto-Regular.ttf',
    bold: 'Roboto-Medium.ttf',
    italics: 'Roboto-Italic.ttf',
    bolditalics: 'Roboto-MediumItalic.ttf'
  }
};

// Configure marked for markdown to plain text conversion
marked.setOptions({
  breaks: true,
  gfm: true
});

/**
 * Converts markdown to plain text (no HTML)
 */
function markdownToText(markdown) {
  if (!markdown) return '';
  try {
    // Use { async: false } to keep markdownToText synchronous even with marked v15+
    const html = marked.parse(markdown, { async: false });
    // Then convert HTML to plain text
    const div = document.createElement('div');
    div.innerHTML = html;
    return div.textContent || div.innerText || '';
  } catch (error) {
    console.warn('Error converting markdown:', error);
    return markdown;
  }
}

/**
 * Gets short model name (without provider prefix)
 */
function getShortModelName(model) {
  return model.split('/')[1] || model;
}

function getFullModelName(model) {
  return model || 'Unknown model';
}

function uniqueValues(values) {
  return [...new Set(values.filter(Boolean))];
}

function formatPrice(value) {
  if (value === undefined || value === null || value === '') return 'n/a';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return String(value);
  if (numeric === 0) return 'free';
  return `$${numeric.toExponential(3)} / token`;
}

function getExportSource() {
  if (typeof window === 'undefined' || !window.location?.origin) {
    return 'LLM Council';
  }
  return `LLM Council (${window.location.origin})`;
}

function getMessageMetadata(msg, conversation) {
  const effectiveCouncilType = msg.council_type || conversation.council_type;
  const customCouncil = msg.custom_council || msg.metadata?.custom_council;
  const stage1Models = (msg.stage1 || []).map((response) => response.model);
  const stage2Models = (msg.stage2 || []).map((ranking) => ranking.model);
  const orchestrator = msg.stage3?.model || customCouncil?.chairman_model;
  const councilModels = uniqueValues(customCouncil?.models || stage1Models);
  const evaluatedBy = uniqueValues(stage2Models);
  const allModels = uniqueValues([...councilModels, ...evaluatedBy, orchestrator ? [orchestrator] : []]);

  return {
    councilType: effectiveCouncilType,
    customCouncil,
    councilModels,
    evaluatedBy,
    orchestrator,
    allModels,
    modelMetadata: msg.model_metadata || msg.metadata?.model_metadata || {}
  };
}

/**
 * Gets emoji and name for council type
 */
function getCouncilTypeDisplay(councilType) {
  const types = {
    premium: { emoji: '💎', name: 'Premium' },
    economic: { emoji: '💰', name: 'Economic' },
    free: { emoji: '🆓', name: 'Free' },
    custom: { emoji: '⚙', name: 'Custom' }
  };
  return types[councilType] || { emoji: '', name: councilType || 'Premium' };
}

/**
 * Formats ISO date to readable format
 */
function formatDate(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

function addMetadataTable(content, rows) {
  content.push({
    table: {
      widths: [130, '*'],
      body: rows.map(([label, value]) => [
        { text: label, style: 'metadataLabel' },
        { text: value || 'n/a', style: 'metadataValue' }
      ])
    },
    layout: 'lightHorizontalLines',
    margin: [0, 0, 0, 15]
  });
}

function addModelSnapshot(content, modelMetadata, models) {
  const snapshotRows = uniqueValues(models)
    .filter((modelId) => modelMetadata[modelId])
    .map((modelId) => {
      const metadata = modelMetadata[modelId];
      const pricing = metadata.pricing || {};
      return [
        { text: modelId, style: 'tableCell', bold: true },
        { text: metadata.name || modelId, style: 'tableCell' },
        { text: metadata.context_length ? metadata.context_length.toLocaleString('en-US') : 'n/a', style: 'tableCell' },
        { text: formatPrice(pricing.prompt), style: 'tableCell' },
        { text: formatPrice(pricing.completion), style: 'tableCell' }
      ];
    });

  if (snapshotRows.length === 0) return;

  content.push(
    {
      text: 'OpenRouter Model Snapshot',
      style: 'stageTitle',
      color: '#4a90e2',
      margin: [0, 12, 0, 8]
    },
    {
      text: 'Captured when the custom council was validated. Pricing is provider metadata and may change later.',
      style: 'infoText',
      margin: [0, 0, 0, 8]
    },
    {
      table: {
        headerRows: 1,
        widths: ['*', '*', 58, 58, 68],
        body: [
          [
            { text: 'Model ID', style: 'tableHeader' },
            { text: 'Name', style: 'tableHeader' },
            { text: 'Context', style: 'tableHeader' },
            { text: 'Input', style: 'tableHeader' },
            { text: 'Output', style: 'tableHeader' }
          ],
          ...snapshotRows
        ]
      },
      margin: [0, 0, 0, 18]
    }
  );
}

/**
 * Generates data structure for pdfmake
 */
export function generatePdfContent(conversation) {
  const councilType = getCouncilTypeDisplay(conversation.council_type);
  const formattedDate = formatDate(conversation.created_at);
  const exportedAt = formatDate(new Date().toISOString());
  
  const content = [];
  
  // Header
  content.push(
    {
      text: 'LLM Council',
      style: 'header',
      margin: [0, 0, 0, 10]
    },
    {
      text: conversation.title || 'Conversation',
      style: 'subheader',
      margin: [0, 0, 0, 10]
    },
    {
      columns: [
        {
          text: `Date: ${formattedDate}`,
          fontSize: 10,
          color: '#666666'
        },
        {
          text: `Council Type: ${councilType.name}`,
          fontSize: 10,
          color: '#666666',
          alignment: 'right'
        }
      ],
      margin: [0, 0, 0, 20]
    },
    {
      canvas: [
        {
          type: 'line',
          x1: 0,
          y1: 0,
          x2: 515,
          y2: 0,
          lineWidth: 2,
          lineColor: '#4a90e2'
        }
      ],
      margin: [0, 0, 0, 20]
    },
    {
      text: 'Export Details',
      style: 'stageTitle',
      color: '#4a90e2',
      margin: [0, 0, 0, 8]
    }
  );

  addMetadataTable(content, [
    ['Source', getExportSource()],
    ['Conversation ID', conversation.id || 'n/a'],
    ['Conversation created', formattedDate || 'n/a'],
    ['Exported at', exportedAt || 'n/a']
  ]);
  
  // Messages
  conversation.messages.forEach((msg, index) => {
    if (index > 0) {
      content.push({
        canvas: [
          {
            type: 'line',
            x1: 0,
            y1: 0,
            x2: 515,
            y2: 0,
            lineWidth: 1,
            lineColor: '#e0e0e0',
            dash: { length: 5 }
          }
        ],
        margin: [0, 20, 0, 20]
      });
    }
    
    // User message
    if (msg.role === 'user') {
      content.push(
        {
          text: 'User Question',
          style: 'sectionTitle',
          color: '#4a90e2',
          margin: [0, 0, 0, 8]
        },
        {
          text: markdownToText(msg.content),
          style: 'userMessage',
          margin: [0, 0, 0, 15]
        }
      );
    }
    
    // Assistant response
    if (msg.role === 'assistant') {
      // Fallback: use message council_type, or conversation (legacy messages)
      const messageMetadata = getMessageMetadata(msg, conversation);
      const msgCouncilType = getCouncilTypeDisplay(messageMetadata.councilType);

      content.push({
        text: `LLM Council Response ${msgCouncilType.name}`,
        style: 'sectionTitle',
        color: '#4a90e2',
        margin: [0, 0, 0, 15]
      });

      addMetadataTable(content, [
        ['Council type', msgCouncilType.name],
        ['Council models', messageMetadata.councilModels.map(getFullModelName).join('\n')],
        ['Peer reviewers', messageMetadata.evaluatedBy.map(getFullModelName).join('\n')],
        ['Orchestrator', getFullModelName(messageMetadata.orchestrator)],
        ['All models used', messageMetadata.allModels.map(getFullModelName).join('\n')]
      ]);

      addModelSnapshot(content, messageMetadata.modelMetadata, messageMetadata.allModels);
      
      // Stage 1: Individual Responses
      if (msg.stage1 && msg.stage1.length > 0) {
        content.push(
          {
            text: 'Stage 1: Individual Responses',
            style: 'stageTitle',
            color: '#4a90e2',
            margin: [0, 15, 0, 10]
          }
        );
        
        msg.stage1.forEach((response, idx) => {
          content.push(
            {
              text: getFullModelName(response.model),
              style: 'modelName',
              margin: [0, idx > 0 ? 10 : 0, 0, 5]
            },
            {
              text: markdownToText(response.response),
              style: 'responseText',
              margin: [0, 0, 0, 15]
            }
          );
          
          if (idx < msg.stage1.length - 1) {
            content.push({
              canvas: [
                {
                  type: 'line',
                  x1: 0,
                  y1: 0,
                  x2: 515,
                  y2: 0,
                  lineWidth: 0.5,
                  lineColor: '#e0e0e0'
                }
              ],
              margin: [0, 5, 0, 5]
            });
          }
        });
      }
      
      // Stage 2: Peer Rankings
      if (msg.stage2 && msg.stage2.length > 0) {
        content.push(
          {
            text: 'Stage 2: Peer Rankings',
            style: 'stageTitle',
            color: '#ff9800',
            margin: [0, 20, 0, 10]
          },
          {
            text: 'Each model evaluated all responses (anonymous as Response A, B, C, etc.) and provided rankings.',
            style: 'infoText',
            margin: [0, 0, 0, 15]
          }
        );
        
        msg.stage2.forEach((ranking, idx) => {
          content.push(
            {
              text: `Evaluation by ${getFullModelName(ranking.model)}`,
              style: 'modelName',
              margin: [0, idx > 0 ? 15 : 0, 0, 5]
            },
            {
              text: markdownToText(ranking.ranking),
              style: 'responseText',
              margin: [0, 0, 0, 10]
            }
          );
          
          // Extracted ranking
          if (ranking.parsed_ranking && ranking.parsed_ranking.length > 0) {
            const rankingList = ranking.parsed_ranking.map((label, rankIdx) => {
              const modelName = msg.metadata?.label_to_model?.[label]
                ? getFullModelName(msg.metadata.label_to_model[label])
                : label;
              return `${rankIdx + 1}. ${modelName}`;
            }).join('\n');
            
            content.push(
              {
                text: 'Extracted Ranking:',
                style: 'labelText',
                margin: [0, 10, 0, 5]
              },
              {
                text: rankingList,
                style: 'responseText',
                margin: [0, 0, 0, 15]
              }
            );
          }
          
          if (idx < msg.stage2.length - 1) {
            content.push({
              canvas: [
                {
                  type: 'line',
                  x1: 0,
                  y1: 0,
                  x2: 515,
                  y2: 0,
                  lineWidth: 0.5,
                  lineColor: '#e0e0e0'
                }
              ],
              margin: [0, 5, 0, 5]
            });
          }
        });
        
        // Aggregate Rankings
        if (msg.metadata?.aggregate_rankings && msg.metadata.aggregate_rankings.length > 0) {
          const tableBody = msg.metadata.aggregate_rankings.map((agg, rankIdx) => [
            { text: (rankIdx + 1).toString(), style: 'tableCell' },
            { text: getShortModelName(agg.model), style: 'tableCell', bold: true },
            { text: agg.average_rank.toFixed(2), style: 'tableCell' },
            { text: agg.rankings_count.toString(), style: 'tableCell' }
          ]);
          
          content.push(
            {
              text: 'Aggregate Rankings (Street Cred)',
              style: 'stageTitle',
              color: '#4a90e2',
              margin: [0, 20, 0, 10]
            },
            {
              text: 'Combined results from all evaluations (lower score is better):',
              style: 'infoText',
              margin: [0, 0, 0, 10]
            },
            {
              table: {
                headerRows: 1,
                widths: ['*', '*', '*', '*'],
                body: [
                  [
                    { text: '#', style: 'tableHeader' },
                    { text: 'Model', style: 'tableHeader' },
                    { text: 'Average', style: 'tableHeader' },
                    { text: 'Votes', style: 'tableHeader' }
                  ],
                  ...tableBody
                ]
              },
              margin: [0, 0, 0, 20]
            }
          );
        }
      }
      
      // Stage 3: Final Council Answer
      if (msg.stage3) {
        content.push(
          {
            text: 'Stage 3: Final Council Answer',
            style: 'stageTitle',
            color: '#4caf50',
            margin: [0, 20, 0, 10]
          },
            {
              text: `Orchestrator: ${getFullModelName(msg.stage3.model)}`,
              style: 'modelName',
              margin: [0, 0, 0, 8]
            },
          {
            text: markdownToText(msg.stage3.response),
            style: 'finalAnswer',
            margin: [0, 0, 0, 20]
          }
        );
      }
    }
  });
  
  // Footer
  content.push(
    {
      canvas: [
        {
          type: 'line',
          x1: 0,
          y1: 0,
          x2: 515,
          y2: 0,
          lineWidth: 1,
          lineColor: '#e0e0e0'
        }
      ],
      margin: [0, 30, 0, 10]
    },
    {
      text: `Generated by ${getExportSource()} - ${exportedAt}`,
      style: 'footer',
      alignment: 'center',
      margin: [0, 10, 0, 0]
    }
  );
  
  return content;
}

/**
 * Exports a complete conversation to PDF with selectable text
 * @param {Object} conversation - Conversation object with all messages and stages
 */
export async function exportConversationToPDF(conversation) {
  if (!conversation || !conversation.messages || conversation.messages.length === 0) {
    throw new Error('The conversation has no messages to export');
  }
  
  try {
    const content = generatePdfContent(conversation);
    
    const docDefinition = {
      content: content,
      defaultStyle: {
        font: 'Roboto', // Roboto is included with pdfmake
        fontSize: 11,
        lineHeight: 1.5
      },
      styles: {
        header: {
          fontSize: 24,
          bold: true,
          color: '#4a90e2'
        },
        subheader: {
          fontSize: 18,
          color: '#333333',
          margin: [0, 0, 0, 10]
        },
        sectionTitle: {
          fontSize: 14,
          bold: true,
          margin: [0, 0, 0, 8]
        },
        stageTitle: {
          fontSize: 16,
          bold: true,
          margin: [0, 15, 0, 10]
        },
        modelName: {
          fontSize: 12,
          bold: true,
          color: '#333333',
          noWrap: false
        },
        userMessage: {
          fontSize: 11,
          color: '#333333',
          background: '#f5f5f5',
          margin: [0, 0, 0, 15]
        },
        responseText: {
          fontSize: 10,
          color: '#555555',
          lineHeight: 1.6
        },
        finalAnswer: {
          fontSize: 11,
          color: '#333333',
          lineHeight: 1.6,
          background: '#f0fff0'
        },
        infoText: {
          fontSize: 9,
          color: '#666666',
          italics: true
        },
        labelText: {
          fontSize: 10,
          bold: true,
          color: '#666666'
        },
        tableHeader: {
          bold: true,
          fontSize: 10,
          color: '#333333',
          fillColor: '#e3f2fd'
        },
        tableCell: {
          fontSize: 10,
          color: '#333333',
          noWrap: false
        },
        metadataLabel: {
          fontSize: 9,
          bold: true,
          color: '#475569',
          fillColor: '#f8fafc'
        },
        metadataValue: {
          fontSize: 9,
          color: '#333333',
          noWrap: false
        },
        footer: {
          fontSize: 9,
          color: '#999999'
        }
      },
      pageSize: 'A4',
      pageMargins: [40, 60, 40, 60],
      info: {
        title: `LLM Council - ${conversation.title || 'Conversation'}`,
        author: 'LLM Council',
        subject: 'LLM Council Conversation',
        keywords: 'LLM Council, OpenRouter, model council, AI conversation export'
      }
    };
    
    const filename = `llm-council-${(conversation.title || 'conversation').replace(/[^a-z0-9]/gi, '-').toLowerCase()}-${new Date().toISOString().split('T')[0]}.pdf`;
    
    pdfMake.createPdf(docDefinition).download(filename);
    
    console.log('PDF generated successfully with pdfmake (selectable text)');
  } catch (error) {
    console.error('Error generating PDF:', error);
    throw new Error('Error generating PDF: ' + error.message);
  }
}
