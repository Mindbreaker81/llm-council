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
    // First convert markdown to HTML
    const html = marked.parse(markdown);
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
 * Converts markdown to basic formatted text for pdfmake
 * Returns an array of text objects with styles
 */
function markdownToPdfText(markdown) {
  if (!markdown) return '';
  const text = markdownToText(markdown);
  // Split into paragraphs and lines
  const lines = text.split('\n').filter(line => line.trim());
  const result = [];
  
  lines.forEach((line, index) => {
    if (line.trim()) {
      result.push(line);
      if (index < lines.length - 1) {
        result.push({ text: '\n' });
      }
    }
  });
  
  return result.length > 0 ? result : text;
}

/**
 * Gets short model name (without provider prefix)
 */
function getShortModelName(model) {
  return model.split('/')[1] || model;
}

/**
 * Gets emoji and name for council type
 */
function getCouncilTypeDisplay(councilType) {
  const types = {
    premium: { emoji: '💎', name: 'Premium' },
    economic: { emoji: '💰', name: 'Economic' },
    free: { emoji: '🆓', name: 'Free' }
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

/**
 * Generates data structure for pdfmake
 */
function generatePdfContent(conversation) {
  const councilType = getCouncilTypeDisplay(conversation.council_type);
  const formattedDate = formatDate(conversation.created_at);
  
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
          text: `Council Type: ${councilType.emoji} ${councilType.name}`,
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
    }
  );
  
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
      const effectiveCouncilType = msg.council_type || conversation.council_type;
      const msgCouncilType = getCouncilTypeDisplay(effectiveCouncilType);

      content.push({
        text: `LLM Council Response ${msgCouncilType.emoji} ${msgCouncilType.name}`,
        style: 'sectionTitle',
        color: '#4a90e2',
        margin: [0, 0, 0, 15]
      });
      
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
              text: getShortModelName(response.model),
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
              text: `Evaluation by ${getShortModelName(ranking.model)}`,
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
                ? getShortModelName(msg.metadata.label_to_model[label])
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
            text: `Chairman: ${getShortModelName(msg.stage3.model)}`,
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
      text: `Generated by LLM Council - ${new Date().toLocaleDateString('en-US')}`,
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
          color: '#333333'
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
          color: '#333333'
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
        subject: 'LLM Council Conversation'
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
