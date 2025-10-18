"use client"

import { useState, useEffect, useRef } from "react"
import { useParams, useRouter } from "next/navigation"
import { ArrowLeft, Download, Share2, Calendar, Building, MapPin, Hash, Square, Circle, RectangleHorizontal, FileText, Copy, Check, ChevronLeft, ChevronRight, ZoomIn, ZoomOut } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Dialog, DialogContent } from "@/components/ui/dialog"
import { useToast } from "@/hooks/use-toast"
import { format } from "date-fns"
import { Skeleton } from "@/components/ui/skeleton"

interface ResultData {
  id: number
  tracking_url: string
  run_date?: string
  company?: string
  jobsite?: string
  text?: string
  status: string
  created_at: string
  step_results: {
    blue_x_shapes: number
    red_squares: number
    pink_shapes: number
    green_rectangles: number
    orange_rectangles: number
    total_detections: number
  }
  cloudinary_urls: {
    step4_results?: string
    step5_results?: string
    step6_results?: string
    step7_results?: string
    step8_results?: string
    step9_results?: string
    step10_results?: string
  }
}

export default function ResultsPage() {
  const params = useParams()
  const router = useRouter()
  const { toast } = useToast()
  const [result, setResult] = useState<ResultData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedImageIndex, setSelectedImageIndex] = useState(0)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [copied, setCopied] = useState(false)
  const [magnifierPosition, setMagnifierPosition] = useState({ x: 0, y: 0 })
  const [showMagnifier, setShowMagnifier] = useState(false)
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 })
  const imageRef = useRef<HTMLImageElement>(null)

  useEffect(() => {
    const fetchResult = async () => {
      try {
        setLoading(true)
        const response = await fetch(`/api/takeoffs?tracking_url=${params.id}`)
        const data = await response.json()

        if (data.success && data.data) {
          setResult(data.data)
        } else {
          setError(data.error || data.message || 'Failed to load result')
        }
      } catch (err) {
        setError('Network error occurred')
        console.error('Error fetching result:', err)
      } finally {
        setLoading(false)
      }
    }

    if (params.id) {
      fetchResult()
    }
  }, [params.id])

  const handleCopyText = async () => {
    if (!result?.text) return
    
    try {
      await navigator.clipboard.writeText(result.text)
      setCopied(true)
      toast({
        title: "Copied!",
        description: "Text copied to clipboard",
      })
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      toast({
        title: "Failed to copy",
        description: "Could not copy to clipboard",
        variant: "destructive",
      })
    }
  }

  const handleDownload = () => {
    if (!result) return

    const content = `
AI-TakeOff Analysis Results
===========================

File: ${result.tracking_url}
Date: ${result.run_date ? format(new Date(result.run_date), 'PPP') : 'N/A'}
Company: ${result.company || 'N/A'}
Jobsite: ${result.jobsite || 'N/A'}

Detection Results:
-----------------
Blue X Shapes: ${result.step_results.blue_x_shapes}
Red Squares: ${result.step_results.red_squares}
Pink Shapes: ${result.step_results.pink_shapes}
Green Rectangles: ${result.step_results.green_rectangles}
Orange Rectangles: ${result.step_results.orange_rectangles}
Total Detections: ${result.step_results.total_detections}

Extracted Text:
--------------
${result.text || 'No text available'}
`

    const blob = new Blob([content], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `${result.tracking_url}_analysis.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    toast({
      title: "Download started",
      description: "Analysis results are being downloaded",
    })
  }

  // Sort images to show step10 first, then descending order
  const imageSteps = result ? Object.entries(result.cloudinary_urls)
    .filter(([_, url]) => url)
    .sort((a, b) => {
      const getStepNumber = (key: string) => {
        const match = key.match(/step(\d+)/)
        return match ? parseInt(match[1]) : 0
      }
      return getStepNumber(b[0]) - getStepNumber(a[0])
    })
    .map(([key, url]) => ({
      key,
      title: key.replace(/_/g, ' ').replace(/step/g, 'Step ').replace(/results/g, '').trim(),
      url: url!
    })) : []

  const detectionStats = result ? [
    { label: 'Blue X Shapes', value: result.step_results.blue_x_shapes, icon: Hash },
    { label: 'Red Squares', value: result.step_results.red_squares, icon: Square },
    { label: 'Pink Shapes', value: result.step_results.pink_shapes, icon: Circle },
    { label: 'Green Rectangles', value: result.step_results.green_rectangles, icon: RectangleHorizontal },
    ...(result.step_results.orange_rectangles > 0 ? [
      { label: 'Orange Rectangles', value: result.step_results.orange_rectangles, icon: RectangleHorizontal }
    ] : [])
  ] : []

  const handlePreviousImage = () => {
    setSelectedImageIndex((prev) => (prev > 0 ? prev - 1 : imageSteps.length - 1))
  }

  const handleNextImage = () => {
    setSelectedImageIndex((prev) => (prev < imageSteps.length - 1 ? prev + 1 : 0))
  }

  const handleMouseMove = (e: React.MouseEvent<HTMLImageElement>) => {
    const elem = e.currentTarget
    const { top, left, width, height } = elem.getBoundingClientRect()
    
    // Calculate cursor position relative to image
    const x = e.clientX - left
    const y = e.clientY - top
    
    // Update position and dimensions
    setMagnifierPosition({ x, y })
    setImageDimensions({ width, height })
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container mx-auto px-4 py-8 max-w-7xl">
          <Skeleton className="h-12 w-48 mb-8" />
          <div className="grid gap-6">
            <Skeleton className="h-64 w-full" />
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-32 w-full" />)}
            </div>
            <Skeleton className="h-96 w-full" />
          </div>
        </div>
      </div>
    )
  }

  if (error || !result) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle className="text-red-600">Error Loading Results</CardTitle>
            <CardDescription>{error || 'Result not found'}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => router.push('/')} variant="outline">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Dashboard
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <div className="border-b bg-background">
        <div className="flex items-center justify-between px-6 py-3">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => router.push('/')}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
            <Separator orientation="vertical" className="h-6" />
            <div>
              <h1 className="text-sm font-semibold">{result.tracking_url}</h1>
              <p className="text-xs text-muted-foreground">Analysis Report</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={handleDownload}>
              <Download className="h-4 w-4 mr-1.5" />
              Export
            </Button>
            <Button variant="ghost" size="sm">
              <Share2 className="h-4 w-4 mr-1.5" />
              Share
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content - Two Column Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Column - Image Viewer */}
        <div className="flex-1 flex flex-col bg-muted/30 border-r overflow-hidden">
          {/* Main Image */}
          <div className="flex-1 relative bg-background flex items-center justify-center p-4 min-h-0">
            {imageSteps.length > 0 && (
              <>
                <div className="relative inline-block">
                  <img
                    ref={imageRef}
                    src={imageSteps[selectedImageIndex]?.url}
                    alt={imageSteps[selectedImageIndex]?.title}
                    className="max-h-full max-w-full object-contain"
                    onClick={() => setIsFullscreen(true)}
                    onMouseMove={handleMouseMove}
                    onMouseEnter={() => setShowMagnifier(true)}
                    onMouseLeave={() => setShowMagnifier(false)}
                  />
                  
                  {/* Magnifying Glass */}
                  {showMagnifier && imageDimensions.width > 0 && (
                    <div
                      className="absolute pointer-events-none border border-white rounded-full shadow-2xl bg-white"
                      style={{
                        width: '200px',
                        height: '200px',
                        left: `${magnifierPosition.x - 100}px`,
                        top: `${magnifierPosition.y - 100}px`,
                        overflow: 'hidden',
                      }}
                    >
                      <img
                        src={imageSteps[selectedImageIndex]?.url}
                        alt="Magnified view"
                        style={{
                          position: 'absolute',
                          width: `${imageDimensions.width * 3}px`,
                          height: `${imageDimensions.height * 3}px`,
                          left: `${-magnifierPosition.x * 3 + 100}px`,
                          top: `${-magnifierPosition.y * 3 + 100}px`,
                          maxWidth: 'none',
                          maxHeight: 'none',
                        }}
                      />
                    </div>
                  )}
                </div>
                
                {/* Navigation Arrows */}
                <Button
                  variant="secondary"
                  size="icon"
                  className="absolute left-4 top-1/2 -translate-y-1/2"
                  onClick={handlePreviousImage}
                >
                  <ChevronLeft className="h-5 w-5" />
                </Button>
                <Button
                  variant="secondary"
                  size="icon"
                  className="absolute right-4 top-1/2 -translate-y-1/2"
                  onClick={handleNextImage}
                >
                  <ChevronRight className="h-5 w-5" />
                </Button>

                {/* Image Controls */}
                <div className="absolute top-4 right-4 flex gap-2">
                  <Button
                    variant="secondary"
                    size="icon"
                    onClick={() => setIsFullscreen(true)}
                  >
                    <ZoomIn className="h-4 w-4" />
                  </Button>
                </div>

                {/* Image Title */}
                <div className="absolute bottom-4 left-4 bg-background/90 backdrop-blur-sm px-3 py-1.5 rounded-md border">
                  <p className="text-sm font-medium">{imageSteps[selectedImageIndex]?.title}</p>
                </div>
              </>
            )}
          </div>

          {/* Thumbnail Strip */}
          <div className="border-t bg-background p-3 flex-shrink-0">
            <ScrollArea className="w-full">
              <div className="flex gap-2">
                {imageSteps.map((step, index) => (
                  <button
                    key={step.key}
                    onClick={() => setSelectedImageIndex(index)}
                    className={`relative flex-shrink-0 w-20 h-20 rounded border-2 overflow-hidden transition-all ${
                      selectedImageIndex === index
                        ? 'border-primary ring-2 ring-primary/20'
                        : 'border-border hover:border-primary/50'
                    }`}
                  >
                    <img
                      src={step.url}
                      alt={step.title}
                      className="w-full h-full object-cover"
                    />
                  </button>
                ))}
              </div>
            </ScrollArea>
          </div>
        </div>

        {/* Right Column - Data & Information */}
        <div className="w-96 flex flex-col bg-background">
          <ScrollArea className="flex-1">
            <div className="p-6 space-y-6">
              {/* Project Info */}
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
                  Project Information
                </h3>
                <div className="space-y-2 text-sm">
                  {result.run_date && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Date</span>
                      <span className="font-medium">{format(new Date(result.run_date), 'PP')}</span>
                    </div>
                  )}
                  {result.company && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Company</span>
                      <span className="font-medium">{result.company}</span>
                    </div>
                  )}
                  {result.jobsite && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Jobsite</span>
                      <span className="font-medium">{result.jobsite}</span>
                    </div>
                  )}
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Status</span>
                    <Badge variant="secondary" className="text-xs">{result.status}</Badge>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Detection Summary */}
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
                  Detection Summary
                </h3>
                <div className="bg-muted/50 rounded-lg p-4 mb-3">
                  <div className="text-center">
                    <div className="text-4xl font-bold">{result.step_results.total_detections}</div>
                    <div className="text-xs text-muted-foreground uppercase tracking-wide mt-1">
                      Total Elements
                    </div>
                  </div>
                </div>
                <div className="space-y-2">
                  {detectionStats.map((stat) => {
                    const IconComponent = stat.icon
                    return (
                      <div key={stat.label} className="flex items-center justify-between text-sm py-1.5">
                        <div className="flex items-center gap-2">
                          <IconComponent className="h-4 w-4 text-muted-foreground" />
                          <span className="text-muted-foreground">{stat.label}</span>
                        </div>
                        <span className="font-semibold tabular-nums">{stat.value}</span>
                      </div>
                    )
                  })}
                </div>
              </div>

              <Separator />

              {/* Extracted Text */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Extracted Text
                  </h3>
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-xs h-7"
                    onClick={handleCopyText}
                  >
                    {copied ? <Check className="h-3 w-3 mr-1" /> : <Copy className="h-3 w-3 mr-1" />}
                    {copied ? 'Copied' : 'Copy'}
                  </Button>
                </div>
                {result.text ? (
                  <div className="bg-muted/30 rounded border p-3 max-h-80 overflow-y-auto">
                    <pre className="text-xs leading-relaxed whitespace-pre-wrap font-mono">
                      {result.text}
                    </pre>
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <FileText className="h-8 w-8 mx-auto mb-2 opacity-30" />
                    <p className="text-xs">No text available</p>
                  </div>
                )}
              </div>
            </div>
          </ScrollArea>
        </div>
      </div>

      {/* Fullscreen Image Dialog */}
      <Dialog open={isFullscreen} onOpenChange={setIsFullscreen}>
        <DialogContent className="max-w-[95vw] max-h-[95vh] p-2">
          {imageSteps.length > 0 && (
            <img
              src={imageSteps[selectedImageIndex]?.url}
              alt={imageSteps[selectedImageIndex]?.title}
              className="w-full h-full object-contain"
              onClick={() => setIsFullscreen(false)}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

