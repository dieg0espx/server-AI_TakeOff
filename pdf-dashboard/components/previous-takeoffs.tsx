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
import { useRouter } from "next/navigation"

interface TakeOffData {
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

interface PreviousTakeoffsProps {
  limit?: number
  onViewTakeoff?: (takeoffData: { fileName: string; result: any; company?: string; jobsite?: string }) => void
}

interface TakeOffsResponse {
  success: boolean
  data: TakeOffData[]
  pagination?: {
    total: number
    count: number
    limit: number
    offset: number
    hasMore: boolean
  }
  // Legacy format support
  count?: number
  total?: number
  limit?: number
  offset?: number
  hasMore?: boolean
  message?: string
  error?: string
}

export function PreviousTakeoffs({ limit = 20, onViewTakeoff }: PreviousTakeoffsProps) {
  const [takeoffs, setTakeoffs] = useState<TakeOffData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [totalCount, setTotalCount] = useState<number>(0)
  const [viewLoading, setViewLoading] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const { toast } = useToast()
  const router = useRouter()

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
        const total = data.pagination?.total ?? data.total ?? data.count ?? 0
        setTotalCount(total)
      } else {
        setError(data.error || data.message || 'Failed to fetch take-offs')
      }
    } catch (err) {
      setError('Network error occurred while fetching take-offs')
      console.error('Error fetching takeoffs:', err)
    } finally {
      setLoading(false)
    }
  }

  const getTotalDetections = (takeoff: TakeOffData) => {
    return takeoff.step_results?.total_detections || 0
  }
  
  const getFileName = (takeoff: TakeOffData) => {
    // Use tracking_url as the display name
    return takeoff.tracking_url || `Analysis #${takeoff.id}`
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


  const handleViewTakeoff = (takeoff: TakeOffData) => {
    // Navigate to the dedicated results page
    router.push(`/results/${takeoff.tracking_url}`)
  }

  const handleDeleteTakeoff = async (takeoffId: number) => {
    try {
      setDeletingId(takeoffId.toString())
      
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
          description: data.error || data.message || "Failed to delete analysis result",
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
              {takeoff.cloudinary_urls?.step4_results && (
                <div className="aspect-video w-full overflow-hidden -mt-6 ">
                  <img 
                    src={takeoff.cloudinary_urls.step4_results} 
                    alt={`Analysis results for ${getFileName(takeoff)}`}
                    className="w-full h-full object-cover hover:scale-105 transition-transform duration-200 "
                  />
                </div>
              )}
              <CardHeader >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-sm font-medium truncate" title={getFileName(takeoff)}>
                      {getFileName(takeoff)}
                    </CardTitle>
                    <CardDescription className="text-xs text-muted-foreground mt-1">
                      {takeoff.run_date ? format(new Date(takeoff.run_date), 'PPP') : 'No date'}
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
                      <span className="font-medium">{takeoff.step_results?.blue_x_shapes || 0}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Red Squares:</span>
                      <span className="font-medium">{takeoff.step_results?.red_squares || 0}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Pink Shapes:</span>
                      <span className="font-medium">{takeoff.step_results?.pink_shapes || 0}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Green Rect:</span>
                      <span className="font-medium">{takeoff.step_results?.green_rectangles || 0}</span>
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
                      disabled={viewLoading}
                    >
                      <Eye className="h-3 w-3 mr-1" />
                      View
                    </Button>
                    {takeoff.cloudinary_urls?.step8_results && (
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
                          disabled={deletingId === takeoff.id.toString()}
                        >
                          <Trash2 className="h-3 w-3 mr-1" />
                          {deletingId === takeoff.id.toString() ? 'Deleting...' : 'Delete'}
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>⚠️ Delete Analysis Result</AlertDialogTitle>
                          <AlertDialogDescription asChild>
                            <div className="space-y-2">
                              <div className="font-medium">Are you sure you want to delete this analysis?</div>
                              <div className="text-sm"><strong>File:</strong> {getFileName(takeoff)}</div>
                              {takeoff.company && <div className="text-sm"><strong>Company:</strong> {takeoff.company}</div>}
                              {takeoff.jobsite && <div className="text-sm"><strong>Jobsite:</strong> {takeoff.jobsite}</div>}
                              <div className="text-red-600 font-medium mt-2">⚠️ This action cannot be undone!</div>
                            </div>
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction
                            onClick={() => handleDeleteTakeoff(takeoff.id)}
                            className="bg-red-600 hover:bg-red-700 focus:ring-red-600"
                          >
                            Yes, Delete Permanently
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
