"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog"
import { Calendar, FileText, Building, MapPin, Eye, Download, Trash2 } from "lucide-react"
import { format } from "date-fns"
import { useToast } from "@/hooks/use-toast"

interface TakeOffData {
  id: string
  file_name: string
  file_size: number
  company?: string
  jobsite?: string
  blue_x_shapes: number
  red_squares: number
  pink_shapes: number
  green_rectangles: number
  status: string
  created_at: string
  original_url?: string
  step4_results_url?: string
  step5_results_url?: string
  step6_results_url?: string
  step7_results_url?: string
  step8_results_url?: string
}

interface PreviousTakeoffsProps {
  limit?: number
  onViewTakeoff?: (takeoffData: { fileName: string; result: any; company?: string; jobsite?: string }) => void
}

interface TakeOffsResponse {
  success: boolean
  data: TakeOffData[]
  count: number
  total?: number
  limit?: number
  offset?: number
  hasMore?: boolean
  message?: string
}

export function PreviousTakeoffs({ limit = 20, onViewTakeoff }: PreviousTakeoffsProps) {
  const [takeoffs, setTakeoffs] = useState<TakeOffData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [totalCount, setTotalCount] = useState<number>(0)
  const [viewLoading, setViewLoading] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const { toast } = useToast()

  useEffect(() => {
    fetchTakeoffs()
  }, [limit])

  const fetchTakeoffs = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Use the Next.js API route
      const response = await fetch(`/api/takeoffs?limit=${limit}`)
      const data: TakeOffsResponse = await response.json()
      
      if (data.success) {
        setTakeoffs(data.data)
        setTotalCount(data.total || data.count)
      } else {
        setError(data.message || 'Failed to fetch take-offs')
      }
    } catch (err) {
      setError('Network error occurred while fetching take-offs')
      console.error('Error fetching takeoffs:', err)
    } finally {
      setLoading(false)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const getTotalDetections = (takeoff: TakeOffData) => {
    return takeoff.blue_x_shapes + takeoff.red_squares + takeoff.pink_shapes + takeoff.green_rectangles
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
      case 'processing':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300'
      case 'failed':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300'
    }
  }


  const handleViewTakeoff = async (takeoff: TakeOffData) => {
    if (onViewTakeoff) {
      // Fetch detailed data and navigate to main page
      try {
        setViewLoading(true)
        setError(null)
        
        const response = await fetch(`/api/takeoffs?id=${takeoff.id}`)
        const data = await response.json()
        
        if (data.success && data.data) {
          // Transform database data to match AnalysisResults expected format
          const dbData = data.data
          const transformedData = {
            id: dbData.id,
            status: dbData.status,
            pdf_path: '', // Not stored in database
            pdf_size: dbData.file_size,
            svg_path: '', // Not stored in database
            svg_size: 0, // Not stored in database
            message: 'Analysis completed',
            results: {
              step_results: {
                step5_blue_X_shapes: dbData.blue_x_shapes,
                step6_red_squares: dbData.red_squares,
                step7_pink_shapes: dbData.pink_shapes,
                step8_green_rectangles: dbData.green_rectangles
              },
            cloudinary_urls: {
              original: dbData.original_url || '',
              step4_results: dbData.step4_results_url || '',
              step5_results: dbData.step5_results_url || '',
              step6_results: dbData.step6_results_url || '',
              step7_results: dbData.step7_results_url || '',
              step8_results: dbData.step8_results_url || ''
            },
              extracted_text: dbData.extracted_text || ''
            }
          }
          
          onViewTakeoff({
            fileName: takeoff.file_name,
            result: transformedData,
            company: takeoff.company,
            jobsite: takeoff.jobsite
          })
        } else {
          setError(data.message || 'Failed to fetch detailed takeoff data')
        }
      } catch (err) {
        setError('Network error occurred while fetching detailed takeoff data')
        console.error('Error fetching detailed takeoff:', err)
      } finally {
        setViewLoading(false)
      }
    }
  }

  const handleDeleteTakeoff = async (takeoffId: string) => {
    try {
      setDeletingId(takeoffId)
      
      const response = await fetch(`/api/takeoffs/delete?id=${takeoffId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      
      const data = await response.json()
      
      if (data.success) {
        // Remove the deleted item from the local state
        setTakeoffs(prevTakeoffs => prevTakeoffs.filter(takeoff => takeoff.id !== takeoffId))
        setTotalCount(prevCount => prevCount - 1)
        
        toast({
          title: "Success",
          description: "Analysis result deleted successfully",
        })
      } else {
        toast({
          title: "Error",
          description: data.message || "Failed to delete analysis result",
          variant: "destructive",
        })
      }
    } catch (err) {
      console.error('Error deleting takeoff:', err)
      toast({
        title: "Error",
        description: "Network error occurred while deleting the analysis result",
        variant: "destructive",
      })
    } finally {
      setDeletingId(null)
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          {/* <h2 className="text-2xl font-bold tracking-tight">Previous Take Offs</h2> */}
          <Skeleton className="h-8 w-24" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-3 w-1/2" />
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-2/3" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">

          <Button variant="outline" size="sm" onClick={fetchTakeoffs}>
            Retry
          </Button>
        </div>
        <Alert>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">

        <div className="flex items-center gap-2">
          <Badge variant="secondary">
            {takeoffs.length} of {totalCount} total
          </Badge>
          <Button variant="outline" size="sm" onClick={fetchTakeoffs}>
            Refresh
          </Button>
        </div>
      </div>

      {takeoffs.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-8">
            <FileText className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No History</h3>
            <p className="text-muted-foreground text-center">
              You haven't processed any PDFs yet. Upload your first document to get started.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {takeoffs.map((takeoff) => (
            <Card key={takeoff.id} className="hover:shadow-md transition-shadow overflow-hidden">
              {/* Step 4 Results Image */}
              {takeoff.original_url && (
                <div className="aspect-video w-full overflow-hidden -mt-6 ">
                  <img 
                    src={takeoff.original_url} 
                    alt={`Analysis results for ${takeoff.file_name}`}
                    className="w-full h-full object-cover hover:scale-105 transition-transform duration-200 "
                  />
                </div>
              )}
              <CardHeader >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-sm font-medium truncate" title={takeoff.file_name}>
                      {takeoff.file_name}
                    </CardTitle>
                    <CardDescription className="text-xs text-muted-foreground mt-1">
                      {formatFileSize(takeoff.file_size)}
                    </CardDescription>
                  </div>
                  {/* <Badge className={`text-xs ${getStatusColor(takeoff.status)}`}>
                    {takeoff.status}
                  </Badge> */}
                </div>
              </CardHeader>
              <hr className="w-[90%] mx-auto -my-3" />
              <CardContent className="pt-0">
                <div className="space-y-3">
                  {/* Company and Jobsite */}
                  {(takeoff.company || takeoff.jobsite) && (
                    <div className="space-y-1">
                      {takeoff.company && (
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Building className="h-3 w-3" />
                          <span className="truncate">{takeoff.company}</span>
                        </div>
                      )}
                      {takeoff.jobsite && (
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <MapPin className="h-3 w-3" />
                          <span className="truncate">{takeoff.jobsite}</span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Detection Counts */}
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Blue X:</span>
                      <span className="font-medium">{takeoff.blue_x_shapes}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Red Squares:</span>
                      <span className="font-medium">{takeoff.red_squares}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Pink Shapes:</span>
                      <span className="font-medium">{takeoff.pink_shapes}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Green Rect:</span>
                      <span className="font-medium">{takeoff.green_rectangles}</span>
                    </div>
                  </div>

                  {/* Total Detections */}
                  {/* <div className="pt-2 border-t">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium">Total Detections:</span>
                      <span className="font-bold text-primary">{getTotalDetections(takeoff)}</span>
                    </div>
                  </div> */}

                  {/* Date */}
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Calendar className="h-3 w-3" />
                    <span>{format(new Date(takeoff.created_at), 'MMM dd, yyyy HH:mm')}</span>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2 pt-2">
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="flex-1 text-xs"
                      onClick={() => handleViewTakeoff(takeoff)}
                    >
                      <Eye className="h-3 w-3 mr-1" />
                      View
                    </Button>
                    {takeoff.step8_results_url && (
                      <Button variant="outline" size="sm" className="flex-1 text-xs">
                        <Download className="h-3 w-3 mr-1" />
                        Download
                      </Button>
                    )}
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button 
                          variant="outline" 
                          size="sm" 
                          className="text-xs text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200 hover:border-red-300"
                          disabled={deletingId === takeoff.id}
                        >
                          <Trash2 className="h-3 w-3 mr-1" />
                          {deletingId === takeoff.id ? 'Deleting...' : 'Delete'}
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Delete Analysis Result</AlertDialogTitle>
                          <AlertDialogDescription>
                            Are you sure you want to delete "{takeoff.file_name}"? This action cannot be undone.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction
                            onClick={() => handleDeleteTakeoff(takeoff.id)}
                            className="bg-red-600 hover:bg-red-700"
                          >
                            Delete
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

    </div>
  )
}
