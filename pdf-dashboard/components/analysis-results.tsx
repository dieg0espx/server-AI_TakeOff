"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { Copy, Check, Download, Share, FileText, Image as ImageIcon, BarChart3, Eye, ZoomIn, ExternalLink, Hash, Square, Circle, RectangleHorizontal, RefreshCw, Wand2, Database } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { useToast } from "@/hooks/use-toast"
import { useApiClient } from "@/lib/api-client"

interface AnalysisResultsProps {
  fileName: string
  result: any
  onReset: () => void
  company?: string
  jobsite?: string
}

interface StepResult {
  blue_x_shapes?: number
  red_squares?: number
  pink_shapes?: number
  green_rectangles?: number
  orange_rectangles?: number
  total_detections?: number
  // Legacy field names for backward compatibility
  step5_blue_X_shapes?: number
  step6_red_squares?: number
  step7_pink_shapes?: number
  step8_green_rectangles?: number
}

interface CloudinaryUrls {
  original?: string
  step4_results?: string
  step5_results?: string
  step6_results?: string
  step7_results?: string
  step8_results?: string
  step9_results?: string
  step10_results?: string
}

interface AnalysisData {
  id: string
  status: string
  pdf_path?: string
  pdf_size?: number
  svg_path?: string
  svg_size?: number
  message?: string
  results: {
    step_results: StepResult
    cloudinary_urls: CloudinaryUrls
    extracted_text?: string
  }
}

export function AnalysisResults({ fileName, result, onReset, company, jobsite }: AnalysisResultsProps) {
  const [copied, setCopied] = useState(false)
  const [selectedImage, setSelectedImage] = useState<string | null>(null)
  const [rewrittenText, setRewrittenText] = useState<string | null>(null)
  const [isRewriting, setIsRewriting] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isSaved, setIsSaved] = useState(false)
  const { toast } = useToast()
  const apiClient = useApiClient()

  // Parse the result data
  const analysisData: AnalysisData = typeof result === 'string' ? JSON.parse(result) : result
  const extractedText = analysisData.results.extracted_text || ''

  // Log the received data for debugging
  console.log('📈 ANALYSIS PAGE RECEIVED DATA:')
  console.log('File Name:', fileName)
  console.log('Company:', company)
  console.log('Jobsite:', jobsite)
  console.log('Analysis Data:', analysisData)

  // Automatically enhance text when component loads and save automatically
  useEffect(() => {
    if (extractedText && !rewrittenText && !isRewriting) {
      handleRewriteText()
    }
  }, [extractedText])

  // Automatically save when enhanced text is ready
  useEffect(() => {
    if (rewrittenText && !isSaved && !isSaving) {
      saveAnalysisToDatabase()
    }
  }, [rewrittenText])

  // Remove automatic saving - now user controls when to save
  // useEffect(() => {
  //   if (analysisData && analysisData.id) {
  //     saveAnalysisToDatabase()
  //   }
  // }, [analysisData])

  const handleCopy = async () => {
    try {
      // Always copy the enhanced text if available, otherwise fall back to extracted text
      const textToCopy = rewrittenText || extractedText
      await navigator.clipboard.writeText(textToCopy)
      setCopied(true)
      toast({
        title: "Copied to clipboard",
        description: "Text has been copied to your clipboard.",
      })
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      toast({
        title: "Failed to copy",
        description: "Could not copy to clipboard. Please try again.",
        variant: "destructive",
      })
    }
  }

  const handleDownload = () => {
    // Always download the enhanced text if available, otherwise fall back to extracted text
    const textToDownload = rewrittenText || extractedText
    const blob = new Blob([textToDownload], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `${fileName.replace(".pdf", "")}_analysis.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    toast({
      title: "Download started",
      description: "Analysis results are being downloaded.",
    })
  }

  const handleShare = async () => {
    if (navigator.share) {
      try {
        const resultText = typeof result === 'string' ? result : JSON.stringify(result, null, 2)
        await navigator.share({
          title: `Analysis of ${fileName}`,
          text: resultText,
        })
      } catch (err) {
        // User cancelled sharing
      }
    } else {
      handleCopy()
    }
  }

  const saveAnalysisToDatabase = async () => {
    if (isSaving) return
    
    setIsSaving(true)
    try {
      const stepResults = analysisData.results.step_results
      const cloudinaryUrls = analysisData.results.cloudinary_urls
      
      const formData = new FormData()
      formData.append('id', analysisData.id)
      formData.append('file_name', fileName)
      formData.append('file_size', (analysisData.pdf_size || 0).toString())
      formData.append('blue_x_shapes', (stepResults.blue_x_shapes ?? stepResults.step5_blue_X_shapes ?? 0).toString())
      formData.append('red_squares', (stepResults.red_squares ?? stepResults.step6_red_squares ?? 0).toString())
      formData.append('pink_shapes', (stepResults.pink_shapes ?? stepResults.step7_pink_shapes ?? 0).toString())
      formData.append('green_rectangles', (stepResults.green_rectangles ?? stepResults.step8_green_rectangles ?? 0).toString())
      formData.append('orange_rectangles', (stepResults.orange_rectangles ?? 0).toString())
      formData.append('original_url', cloudinaryUrls.original || '')
      formData.append('step4_results_url', cloudinaryUrls.step4_results || '')
      formData.append('step5_results_url', cloudinaryUrls.step5_results || '')
      formData.append('step6_results_url', cloudinaryUrls.step6_results || '')
      formData.append('step7_results_url', cloudinaryUrls.step7_results || '')
      formData.append('step8_results_url', cloudinaryUrls.step8_results || '')
      formData.append('step9_results_url', cloudinaryUrls.step9_results || '')
      formData.append('step10_results_url', cloudinaryUrls.step10_results || '')
      formData.append('extracted_text', extractedText || '')
      formData.append('enhanced_text', rewrittenText || '') // Include enhanced text if available
      formData.append('status', analysisData.status)
      formData.append('company', company || '')
      formData.append('jobsite', jobsite || '')

      const response = await fetch('https://ai-takeoff.ttfconstruction.com/create.php', {
        method: 'POST',
        body: formData
      })

      const result = await response.json()
      
      if (result.success) {
        setIsSaved(true)
        const enhancedTextNote = rewrittenText ? " (including AI-enhanced text)" : ""
        toast({
          title: "Analysis saved successfully",
          description: `Your analysis results have been saved to the database.${enhancedTextNote}`,
        })
        console.log('Analysis results saved to database:', result.id)
      } else {
        throw new Error(result.message || 'Failed to save analysis results')
      }
    } catch (error) {
      console.error('Error saving analysis to database:', error)
      toast({
        title: "Failed to save analysis",
        description: error instanceof Error ? error.message : "An error occurred while saving the analysis.",
        variant: "destructive",
      })
    } finally {
      setIsSaving(false)
    }
  }

  const handleRewriteText = async () => {
    if (isRewriting) return
    
    setIsRewriting(true)
    try {
      const response = await apiClient.post('/api/rewrite-text', {
        text: extractedText,
        fileName: fileName
      }, { requireAuth: false })

      if (!response.ok) {
        let errorMessage = 'Failed to rewrite text'
        try {
          const errorData = await response.json()
          errorMessage = errorData.error || errorMessage
        } catch (parseError) {
          errorMessage = `HTTP ${response.status}: ${response.statusText}`
        }
        throw new Error(errorMessage)
      }

      const data = await response.json()
      setRewrittenText(data.rewrittenText)
      
      // Update the database with the enhanced text if analysis is already saved
      if (isSaved) {
        await updateEnhancedTextInDatabase(data.rewrittenText)
      }
      
      toast({
        title: "Text rewritten successfully",
        description: "The extracted text has been enhanced with AI.",
      })
    } catch (error) {
      console.error('Error rewriting text:', error)
      toast({
        title: "Failed to rewrite text",
        description: error instanceof Error ? error.message : "An error occurred while rewriting the text.",
        variant: "destructive",
      })
    } finally {
      setIsRewriting(false)
    }
  }

  const updateEnhancedTextInDatabase = async (enhancedText: string) => {
    try {
      const formData = new FormData()
      formData.append('id', analysisData.id)
      formData.append('enhanced_text', enhancedText)

      const response = await fetch('https://ai-takeoff.ttfconstruction.com/update.php', {
        method: 'POST',
        body: formData
      })

      const result = await response.json()
      
      if (result.success) {
        console.log('Enhanced text updated in database')
      } else {
        console.error('Failed to update enhanced text:', result.message)
      }
    } catch (error) {
      console.error('Error updating enhanced text in database:', error)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const renderMarkdown = (text: string) => {
    // Simple markdown renderer for basic formatting
    return text
      .split('\n')
      .map((line, index) => {
        // Handle bold text **text**
        const boldRegex = /\*\*(.*?)\*\*/g
        const parts = line.split(boldRegex)
        
        return (
          <div key={index} className="mb-2">
            {parts.map((part, partIndex) => {
              if (partIndex % 2 === 1) {
                // This is bold text
                return <strong key={partIndex} className="font-semibold">{part}</strong>
              }
              return part
            })}
          </div>
        )
      })
  }

  const stepResults = analysisData.results.step_results
  const cloudinaryUrls = analysisData.results.cloudinary_urls

  const stepConfigs = [
    {
      key: 'blue_x_shapes',
      title: 'Blue X Shapes',
      count: stepResults.blue_x_shapes ?? stepResults.step5_blue_X_shapes ?? 0,
      icon: Hash,
      color: 'bg-blue-500',
      description: 'Detected X-shaped elements in blue'
    },
    {
      key: 'red_squares',
      title: 'Red Squares',
      count: stepResults.red_squares ?? stepResults.step6_red_squares ?? 0,
      icon: Square,
      color: 'bg-red-500',
      description: 'Detected square elements in red'
    },
    {
      key: 'pink_shapes',
      title: 'Pink Shapes',
      count: stepResults.pink_shapes ?? stepResults.step7_pink_shapes ?? 0,
      icon: Circle,
      color: 'bg-pink-500',
      description: 'Detected circular/pink elements'
    },
    {
      key: 'green_rectangles',
      title: 'Green Rectangles',
      count: stepResults.green_rectangles ?? stepResults.step8_green_rectangles ?? 0,
      icon: RectangleHorizontal,
      color: 'bg-green-500',
      description: 'Detected rectangular elements in green'
    },
    ...(stepResults.orange_rectangles ? [{
      key: 'orange_rectangles',
      title: 'Orange Rectangles',
      count: stepResults.orange_rectangles,
      icon: RectangleHorizontal,
      color: 'bg-orange-500',
      description: 'Detected rectangular elements in orange'
    }] : [])
  ]

  const imageSteps = [
    ...(cloudinaryUrls.original ? [{
      key: 'original',
      title: 'Original Image',
      url: cloudinaryUrls.original,
      description: 'Original PDF converted to image'
    }] : []),
    ...(cloudinaryUrls.step4_results ? [{
      key: 'step4_results',
      title: 'Step 4 Results',
      url: cloudinaryUrls.step4_results,
      description: 'Initial processing results'
    }] : []),
    ...(cloudinaryUrls.step5_results ? [{
      key: 'step5_results',
      title: 'Step 5 Results',
      url: cloudinaryUrls.step5_results,
      description: 'Blue X shapes detection'
    }] : []),
    ...(cloudinaryUrls.step6_results ? [{
      key: 'step6_results',
      title: 'Step 6 Results',
      url: cloudinaryUrls.step6_results,
      description: 'Red squares detection'
    }] : []),
    ...(cloudinaryUrls.step7_results ? [{
      key: 'step7_results',
      title: 'Step 7 Results',
      url: cloudinaryUrls.step7_results,
      description: 'Pink shapes detection'
    }] : []),
    ...(cloudinaryUrls.step8_results ? [{
      key: 'step8_results',
      title: 'Step 8 Results',
      url: cloudinaryUrls.step8_results,
      description: 'Green rectangles detection'
    }] : []),
    ...(cloudinaryUrls.step9_results ? [{
      key: 'step9_results',
      title: 'Step 9 Results',
      url: cloudinaryUrls.step9_results,
      description: 'Orange rectangles detection'
    }] : []),
    ...(cloudinaryUrls.step10_results ? [{
      key: 'step10_results',
      title: 'Step 10 Results',
      url: cloudinaryUrls.step10_results,
      description: 'Final comprehensive analysis'
    }] : [])
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      {/* Header with actions */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-primary" />
                AI-Takeoff Analysis Complete
              </CardTitle>
              <CardDescription className="flex items-center gap-2">
                <span>{fileName}</span>
                {analysisData.pdf_size && (
                  <Badge variant="secondary" className="text-xs">
                    {formatFileSize(analysisData.pdf_size)}
                  </Badge>
                )}
                <Badge variant="outline" className="text-xs">
                  {analysisData.status}
                </Badge>
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              {isSaving && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <motion.div 
                    animate={{ rotate: 360 }} 
                    transition={{ duration: 1, repeat: Infinity }}
                  >
                    <RefreshCw className="h-4 w-4" />
                  </motion.div>
                  Saving...
                </div>
              )}
              {isSaved && (
                <div className="flex items-center gap-2 text-sm text-green-600">
                  <Check className="h-4 w-4" />
                  Saved
                </div>
              )}
              <Button variant="outline" size="sm" onClick={handleShare}>
                <Share className="h-4 w-4 mr-2" />
                Share
              </Button>
              <Button variant="outline" size="sm" onClick={handleDownload}>
                <Download className="h-4 w-4 mr-2" />
                Download
              </Button>
              <Button variant="outline" size="sm" onClick={onReset}>
                Upload New File
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Main Content with Accordions */}
      <Accordion type="multiple" defaultValue={["overview", "results"]} className="space-y-4">
        
        {/* Overview Accordion */}
        <AccordionItem value="overview">
          <AccordionTrigger className="text-left">
            <div className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              <span>Processing Overview & Summary</span>
            </div>
          </AccordionTrigger>
          <AccordionContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="h-5 w-5" />
                    Processing Summary
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {analysisData.pdf_size && (
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">PDF Size:</span>
                      <span className="font-medium">{formatFileSize(analysisData.pdf_size)}</span>
                    </div>
                  )}
                  {analysisData.svg_size && (
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">SVG Size:</span>
                      <span className="font-medium">{formatFileSize(analysisData.svg_size)}</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Processing ID:</span>
                    <span className="font-mono text-xs">{analysisData.id}</span>
                  </div>
                  {analysisData.message && (
                    <>
                      <Separator />
                      <div className="text-sm text-muted-foreground">
                        {analysisData.message}
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Hash className="h-5 w-5" />
                    Quick Detection Stats
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4">
                    {stepConfigs.map((step) => {
                      const IconComponent = step.icon
                      return (
                        <div key={step.key} className="flex items-center gap-3">
                          <div className={`w-3 h-3 rounded-full ${step.color}`} />
                          <div className="flex-1">
                            <div className="text-sm font-medium">{step.count}</div>
                            <div className="text-xs text-muted-foreground">{step.title}</div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </CardContent>
              </Card>
            </div>
          </AccordionContent>
        </AccordionItem>

        {/* Step Results Accordion */}
        <AccordionItem value="results">
          <AccordionTrigger className="text-left">
            <div className="flex items-center gap-2">
              <Hash className="h-5 w-5" />
              <span>Detailed Detection Results</span>
              <Badge variant="secondary" className="ml-2">
                {stepConfigs.reduce((sum, step) => sum + step.count, 0)} total
              </Badge>
            </div>
          </AccordionTrigger>
          <AccordionContent>
            <Card className="mt-4">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  AI-Powered Shape Detection Results
                </CardTitle>
                <CardDescription>
                  Detailed analysis of detected structural elements and components
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {stepConfigs.map((step) => {
                    const IconComponent = step.icon
                    return (
                      <motion.div
                        key={step.key}
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ duration: 0.2, delay: stepConfigs.indexOf(step) * 0.1 }}
                      >
                        <Card className="border-l-4 border-l-primary/20">
                          <CardContent className="p-4">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <div className={`p-2 rounded-lg ${step.color} bg-opacity-10`}>
                                  <IconComponent className={`h-5 w-5 ${step.color.replace('bg-', 'text-')}`} />
                                </div>
                                <div>
                                  <div className="font-semibold">{step.title}</div>
                                  <div className="text-sm text-muted-foreground">{step.description}</div>
                                </div>
                              </div>
                              <div className="text-right">
                                <div className="text-2xl font-bold">{step.count}</div>
                                <div className="text-xs text-muted-foreground">detected</div>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      </motion.div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          </AccordionContent>
        </AccordionItem>

        {/* Visual Analysis Accordion */}
        <AccordionItem value="images">
          <AccordionTrigger className="text-left">
            <div className="flex items-center gap-2">
              <ImageIcon className="h-5 w-5" />
              <span>Visual Analysis Results</span>
              <Badge variant="secondary" className="ml-2">
                {imageSteps.length} images
              </Badge>
            </div>
          </AccordionTrigger>
          <AccordionContent>
            <Card className="mt-4">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <ImageIcon className="h-5 w-5" />
                  Step-by-Step Processing Images
                </CardTitle>
                <CardDescription>
                  Visual documentation of the AI analysis process and detection results
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {imageSteps.map((step, index) => (
                    <motion.div
                      key={step.key}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3, delay: index * 0.1 }}
                    >
                      <Card className="overflow-hidden hover:shadow-lg transition-shadow">
                        <div className="aspect-square relative">
                          <img
                            src={step.url}
                            alt={step.title}
                            className="w-full h-full object-cover cursor-pointer"
                            onClick={() => setSelectedImage(step.url)}
                          />
                          <div className="absolute inset-0 bg-black/0 hover:bg-black/10 transition-colors flex items-center justify-center">
                            <Button
                              variant="secondary"
                              size="sm"
                              className="opacity-0 hover:opacity-100 transition-opacity"
                              onClick={() => setSelectedImage(step.url)}
                            >
                              <ZoomIn className="h-4 w-4 mr-2" />
                              View
                            </Button>
                          </div>
                        </div>
                        <CardContent className="p-3">
                          <div className="font-medium text-sm">{step.title}</div>
                          <div className="text-xs text-muted-foreground">{step.description}</div>
                        </CardContent>
                      </Card>
                    </motion.div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </AccordionContent>
        </AccordionItem>

        {/* Text Analysis Accordion */}
        <AccordionItem value="text">
          <AccordionTrigger className="text-left">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              <span>
                {rewrittenText ? "AI-Enhanced Engineering Analysis" : "Extracted Text Analysis"}
              </span>
              {rewrittenText && (
                <Badge variant="outline" className="ml-2">
                  AI Enhanced
                </Badge>
              )}
            </div>
          </AccordionTrigger>
          <AccordionContent>
            <Card className="mt-4">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <FileText className="h-5 w-5" />
                      {rewrittenText ? "Professional Engineering Analysis" : "Document Text Extraction"}
                    </CardTitle>
                    <CardDescription>
                      {rewrittenText 
                        ? "Comprehensive structural engineering analysis with professional formatting"
                        : "Raw text content extracted from the PDF document"
                      }
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-2">
                    {!rewrittenText && (
                      <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={handleRewriteText}
                        disabled={isRewriting}
                        className="gap-2"
                      >
                        <motion.div 
                          animate={{ rotate: isRewriting ? 360 : 0 }} 
                          transition={{ duration: 1, repeat: isRewriting ? Infinity : 0 }}
                        >
                          {isRewriting ? <RefreshCw className="h-4 w-4" /> : <Wand2 className="h-4 w-4" />}
                        </motion.div>
                        {isRewriting ? "Enhancing..." : "Enhance with AI"}
                      </Button>
                    )}
                    <Button variant="outline" size="sm" onClick={handleCopy} className="gap-2">
                      <motion.div animate={{ scale: copied ? 1.1 : 1 }} transition={{ duration: 0.1 }}>
                        {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
                      </motion.div>
                      {copied ? "Copied!" : "Copy Text"}
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="relative">
                  <div className="bg-muted/30 rounded-lg p-6 max-h-96 overflow-y-auto border">
                    {isRewriting ? (
                      <div className="flex items-center justify-center py-8">
                        <div className="flex items-center gap-3">
                          <motion.div
                            animate={{ rotate: 360 }}
                            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                          >
                            <RefreshCw className="h-5 w-5 text-primary" />
                          </motion.div>
                          <span className="text-sm text-muted-foreground">AI is enhancing the text...</span>
                        </div>
                      </div>
                    ) : (
                      <div className="text-sm leading-relaxed text-foreground">
                        {renderMarkdown(rewrittenText || extractedText)}
                      </div>
                    )}
                  </div>
                  <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-background to-transparent pointer-events-none rounded-b-lg" />
                </div>
                <Separator className="my-4" />
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>
                    {rewrittenText 
                      ? "Engineering analysis completed on " + new Date().toLocaleDateString()
                      : "Text extracted on " + new Date().toLocaleDateString()
                    }
                  </span>
                  <span>
                    {(rewrittenText || extractedText).split(" ").length} words • {(rewrittenText || extractedText).split("\n").length} lines
                  </span>
                </div>
              </CardContent>
            </Card>
          </AccordionContent>
        </AccordionItem>
      </Accordion>

      {/* Image Modal */}
      <Dialog open={!!selectedImage} onOpenChange={() => setSelectedImage(null)}>
        <DialogContent className="max-w-4xl max-h-[90vh] p-0">
          <DialogHeader className="p-6 pb-0">
            <DialogTitle>Analysis Result Image</DialogTitle>
          </DialogHeader>
          {selectedImage && (
            <div className="p-6 pt-0">
              <img
                src={selectedImage}
                alt="Analysis result"
                className="w-full h-auto max-h-[70vh] object-contain rounded-lg"
              />
            </div>
          )}
        </DialogContent>
      </Dialog>
    </motion.div>
  )
}
