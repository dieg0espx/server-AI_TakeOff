import { NextRequest, NextResponse } from 'next/server'

export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const id = searchParams.get('id')

    if (!id) {
      return NextResponse.json(
        { success: false, message: 'ID parameter is required' },
        { status: 400 }
      )
    }

    // Use the new API endpoint
    const phpUrl = `https://ttfconstruction.com/ai-takeoff-results/delete.php?id=${id}`
    
    const response = await fetch(phpUrl)
    const data = await response.json()

    if (!response.ok) {
      return NextResponse.json(
        { success: false, message: data.error || data.message || 'Failed to delete take-off' },
        { status: response.status }
      )
    }

    return NextResponse.json(data)
  } catch (error) {
    console.error('Error deleting take-off:', error)
    return NextResponse.json(
      { success: false, message: 'Internal server error' },
      { status: 500 }
    )
  }
}
