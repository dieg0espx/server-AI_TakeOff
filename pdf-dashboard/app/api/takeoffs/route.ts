import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const limit = parseInt(searchParams.get('limit') || '20')
    const id = searchParams.get('id')
    const trackingUrl = searchParams.get('tracking_url')

    // Use the new API endpoints
    let phpUrl: string
    
    if (id || trackingUrl) {
      // Fetch single record by ID or tracking_url
      const param = trackingUrl ? `tracking_url=${trackingUrl}` : `tracking_url=${id}`
      phpUrl = `https://ttfconstruction.com/ai-takeoff-results/read.php?${param}`
    } else {
      // Fetch all records with pagination
      phpUrl = `https://ttfconstruction.com/ai-takeoff-results/read_all.php?limit=${limit}`
    }
    
    const response = await fetch(phpUrl)
    const data = await response.json()

    if (!response.ok) {
      return NextResponse.json(
        { success: false, message: data.error || data.message || 'Failed to fetch take-offs' },
        { status: response.status }
      )
    }

    return NextResponse.json(data)
  } catch (error) {
    console.error('Error fetching take-offs:', error)
    return NextResponse.json(
      { success: false, message: 'Internal server error' },
      { status: 500 }
    )
  }
}
