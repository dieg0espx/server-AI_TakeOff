import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const { text, fileName } = await request.json()

    if (!text || typeof text !== 'string') {
      return NextResponse.json({ error: 'No valid text provided' }, { status: 400 })
    }

    if (text.trim().length === 0) {
      return NextResponse.json({ error: 'Text cannot be empty' }, { status: 400 })
    }

    // Check if OpenAI API key is configured
    const openaiApiKey = process.env.OPENAI_API_KEY
    if (!openaiApiKey) {
      console.error('OpenAI API key not configured')
      return NextResponse.json({ error: 'OpenAI API key not configured' }, { status: 500 })
    }

    // Call OpenAI API to rewrite the text
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${openaiApiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'gpt-3.5-turbo',
        messages: [
          {
            role: 'system',
            content: `You are a professional structural engineer specializing in concrete construction and slab systems. Your task is to analyze and rewrite extracted text from construction drawings and specifications to provide comprehensive, professional engineering documentation.

CRITICAL REQUIREMENTS:
- Write ONLY as a professional structural engineer with expertise in concrete construction
- Use ONLY the information provided in the extracted text - do not add external knowledge
- Expand and elaborate on the provided information to create comprehensive documentation
- Use proper engineering terminology and construction industry standards
- Structure the response as a professional engineering report

PROFESSIONAL ENGINEERING FOCUS:
1. **Structural Analysis**: Interpret structural elements, load requirements, and design specifications
2. **Construction Methodology**: Detail construction processes, sequencing, and installation requirements
3. **Material Specifications**: Expand on concrete mixes, reinforcement, and material requirements
4. **Safety & Compliance**: Highlight safety requirements, inspection protocols, and code compliance
5. **Technical Details**: Provide detailed explanations of structural components and their functions
6. **Quality Control**: Include inspection requirements, testing protocols, and quality standards

FORMATTING REQUIREMENTS:
- Use **bold text** for all measurements, specifications, and critical technical information
- Structure with clear engineering sections and subsections
- Use bullet points for technical specifications and requirements
- Include detailed explanations of structural elements and their purposes
- Maintain professional engineering documentation standards
- Expand on abbreviations and technical terms with full explanations
- Provide context for all structural elements and their relationships

EXPANSION GUIDELINES:
- Take every piece of information and expand it with professional engineering context
- Explain the purpose and function of each structural element mentioned
- Detail the construction sequence and methodology
- Include relevant engineering calculations and design considerations
- Explain the relationship between different structural components
- Provide comprehensive coverage of all technical aspects mentioned in the original text`
          },
          {
            role: 'user',
            content: `As a professional structural engineer, please analyze and rewrite the following extracted text from the construction document "${fileName}". 

Transform this information into a comprehensive professional engineering report that:
- Expands on every technical detail provided
- Explains the structural purpose and function of each element
- Details construction methodology and sequencing
- Includes relevant engineering specifications and requirements
- Uses proper structural engineering terminology
- Provides context for all measurements, materials, and structural components

Extracted text to analyze:
${text}`
          }
        ],
        max_tokens: 4000,
        temperature: 0.3,
      }),
    })

    if (!response.ok) {
      const errorData = await response.json()
      console.error('OpenAI API error:', errorData)
      return NextResponse.json({ error: 'Failed to process text with OpenAI' }, { status: 500 })
    }

    const data = await response.json()
    const rewrittenText = data.choices[0]?.message?.content

    if (!rewrittenText) {
      return NextResponse.json({ error: 'No response from OpenAI' }, { status: 500 })
    }

    return NextResponse.json({ 
      rewrittenText,
      originalText: text,
      fileName 
    })

  } catch (error) {
    console.error('Error rewriting text:', error)
    
    // Provide more specific error messages
    if (error instanceof Error) {
      if (error.message.includes('fetch')) {
        return NextResponse.json({ error: 'Network error connecting to OpenAI API' }, { status: 500 })
      }
      if (error.message.includes('JSON')) {
        return NextResponse.json({ error: 'Invalid response format from OpenAI API' }, { status: 500 })
      }
      return NextResponse.json({ error: `Server error: ${error.message}` }, { status: 500 })
    }
    
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
