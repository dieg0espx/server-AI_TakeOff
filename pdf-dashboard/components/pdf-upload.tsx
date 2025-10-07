"use client"

import type React from "react"
import { useState, useCallback, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Upload, FileText, X, AlertCircle, LogOut } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { useAuth } from "@/context/AuthContext"
import { GoogleLoginButton } from "@/components/google-login-button"
import { CompanyJobsiteSelector } from "@/components/company-jobsite-selector"
import { useApiClient } from "@/lib/api-client"
import axios from "axios"

interface PdfUploadProps {
  onFileUpload: (file: File, uploadResponse: { id: string; status: string; message: string; company?: string; jobsite?: string }) => void
}

export function PdfUpload({ onFileUpload }: PdfUploadProps) {
  const { accessToken, setAccessToken, isAuthenticated } = useAuth()
  const apiClient = useApiClient()
  const [isDragOver, setIsDragOver] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [fileUrl, setFileUrl] = useState<string | null>(null)
  const [selectedCompany, setSelectedCompany] = useState<string | null>(null)
  const [selectedJobsite, setSelectedJobsite] = useState<string | null>(null)
  const [selectionConfirmed, setSelectionConfirmed] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const validateFile = (file: File): boolean => {
    if (file.type !== "application/pdf") {
      setError("Please select a PDF file only")
      return false
    }
    if (file.size > 10 * 1024 * 1024) {
      // 10MB limit
      setError("File size must be less than 10MB")
      return false
    }
    setError(null)
    return true
  }

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(false)

    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) {
      const file = files[0]
      if (validateFile(file)) {
        setSelectedFile(file)
        setFileUrl(URL.createObjectURL(file))
      }
    }
  }, [])

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files
      if (files && files.length > 0) {
        const file = files[0]
        if (validateFile(file)) {
          setSelectedFile(file)
          setFileUrl(URL.createObjectURL(file))
        }
      }
      e.target.value = ""
    },
    [],
  )

  // Google Drive Upload Algorithm
  const uploadFileToDrive = async () => {
    if (!accessToken) {
      setError("Please log in first!")
      return
    }
    if (!selectedFile) {
      setError("Please select a file first!")
      return
    }

    setUploading(true)
    setIsProcessing(true)
    setError(null)

    try {
      // Step 1: Find or Create "AI-TakeOff" folder
      let folderId
      const folderSearchResponse = await apiClient.get(
        `https://www.googleapis.com/drive/v3/files?q=name='AI-TakeOff' and mimeType='application/vnd.google-apps.folder'&spaces=drive`
      )

      const folderSearchResult = await folderSearchResponse.json()
      if (folderSearchResult.files.length > 0) {
        folderId = folderSearchResult.files[0].id
        console.log("📂 Found AI-TakeOff folder:", folderId)
      } else {
        // Folder doesn't exist, create it
        const folderCreateResponse = await apiClient.post("https://www.googleapis.com/drive/v3/files", {
          name: "AI-TakeOff",
          mimeType: "application/vnd.google-apps.folder",
        })

        const folderCreateResult = await folderCreateResponse.json()
        folderId = folderCreateResult.id
        console.log("📂 Created AI-TakeOff folder:", folderId)
      }

      // Step 2: Upload file to the AI-TakeOff folder
      const metadata = { name: selectedFile.name, mimeType: selectedFile.type, parents: [folderId] }
      const form = new FormData()
      form.append("metadata", new Blob([JSON.stringify(metadata)], { type: "application/json" }))
      form.append("file", selectedFile)

      const uploadResponse = await apiClient.request(
        "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
        {
          method: "POST",
          body: form,
        }
      )

      const uploadResult = await uploadResponse.json()
      console.log("✅ File Uploaded:", uploadResult)

      // Step 3: Make file public
      await apiClient.post(`https://www.googleapis.com/drive/v3/files/${uploadResult.id}/permissions`, {
        role: "reader",
        type: "anyone"
      })

      console.log("✅ File uploaded successfully! Now calling the server...")

      // Step 4: Call the AI processing server
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://server-aitakeoff-production.up.railway.app'
      console.log(`🌐 Calling server at: ${apiUrl}/AI-Takeoff/${uploadResult.id}`)
      
      const serverResponse = await axios.get(
        `${apiUrl}/AI-Takeoff/${uploadResult.id}`,
        { headers: { "Content-Type": "application/json" } }
      )

      // Server returns a URL - print it to console
      console.log('📎 RECEIVED URL FROM SERVER:')
      console.log(serverResponse.data)

      // Step 5: Call the returned URL to get the actual analysis data
      const dataUrl = serverResponse.data
      console.log(`🔍 Fetching analysis data from: ${dataUrl}`)
      
      const analysisResponse = await axios.get(dataUrl, {
        headers: { "Content-Type": "application/json" }
      })

      console.log('✅ ANALYSIS DATA RECEIVED:')
      console.log(analysisResponse.data)

      if (analysisResponse.data.success && analysisResponse.data.data) {
        const analysisData = analysisResponse.data.data
        
        // Transform the data to match the expected format for the analysis page
        const transformedData = {
          id: analysisData.id.toString(),
          status: analysisData.status,
          message: 'Analysis completed successfully',
          results: {
            step_results: analysisData.step_results,
            cloudinary_urls: analysisData.cloudinary_urls,
            extracted_text: '' // Will be populated if needed
          },
          company: selectedCompany || analysisData.company,
          jobsite: selectedJobsite || analysisData.jobsite
        }
        
        console.log('📊 TRANSFORMED DATA FOR ANALYSIS PAGE:')
        console.log(transformedData)
        
        // Pass the transformed data to the analysis page
        onFileUpload(selectedFile, transformedData)
      } else {
        console.error('❌ Failed to fetch analysis data:', analysisResponse.data)
        setError("Failed to fetch analysis data")
      }
    } catch (error) {
      console.error("❌ Upload Error:", error)
      setError("Upload failed. Please try again.")
    } finally {
      setUploading(false)
      setIsProcessing(false)
    }
  }

  const handleRemoveFile = () => {
    setSelectedFile(null)
    setFileUrl(null)
    setError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  const handleBrowseClick = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    fileInputRef.current?.click()
  }

  const handleLogout = () => {
    setAccessToken(null)
    setSelectedFile(null)
    setFileUrl(null)
    setError(null)
  }

  const handleCompanySelect = (company: string) => {
    setSelectedCompany(company)
    console.log('Selected Company:', company)
  }

  const handleJobsiteSelect = (jobsite: string) => {
    setSelectedJobsite(jobsite)
    console.log('Selected Jobsite:', jobsite)
  }

  const handleSelectionConfirmed = () => {
    setSelectionConfirmed(true)
  }

  if (!isAuthenticated) {
    return (
      <Card className="border-dashed border-2 border-muted-foreground/25 bg-card/50">
        <CardContent className="p-8">
          <div className="flex flex-col items-center justify-center space-y-6 py-8">
            <div className="text-center space-y-2">
              <h3 className="text-lg font-semibold">Welcome to AI-TakeOff</h3>
              <p className="text-sm text-muted-foreground">
                Sign in with Google to upload and analyze your PDF documents with AI-powered insights.
              </p>
            </div>
            <GoogleLoginButton />
          </div>
        </CardContent>
      </Card>
    )
  }

  // V0-style loading page
  if (isProcessing) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Card className="w-full max-w-2xl border-0 shadow-2xl bg-gradient-to-br from-background to-muted/20">
          <CardContent className="p-12">
            <div className="text-center space-y-8">
              {/* Animated Logo/Icon */}
              <div className="relative mx-auto w-20 h-20">
                <div className="absolute inset-0 rounded-full bg-gradient-to-r from-primary/20 to-primary/40 animate-pulse"></div>
                <div className="absolute inset-2 rounded-full bg-gradient-to-r from-primary to-primary/80 flex items-center justify-center">
                  <svg className="w-8 h-8 text-white animate-bounce" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
              </div>

              {/* Main Title */}
              <div className="space-y-2">
                <h1 className="text-3xl font-bold bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent">
                  Building Your Analysis
                </h1>
                <p className="text-lg text-muted-foreground">
                  Processing your PDF with AI-powered analysis
                </p>
              </div>

              {/* Progress Steps */}
              <div className="space-y-4">
                <div className="flex items-center justify-center space-x-4">
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                    <span className="text-sm font-medium text-green-600">Upload Complete</span>
                  </div>
                  <div className="w-8 h-0.5 bg-primary/30"></div>
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 bg-primary rounded-full animate-pulse"></div>
                    <span className="text-sm font-medium text-primary">Processing</span>
                  </div>
                  <div className="w-8 h-0.5 bg-muted-foreground/20"></div>
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 bg-muted-foreground/30 rounded-full"></div>
                    <span className="text-sm text-muted-foreground">Analysis</span>
                  </div>
                </div>
              </div>

              {/* Animated Progress Bar */}
              <div className="w-full max-w-md mx-auto">
                <div className="h-2 bg-muted-foreground/20 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-primary to-primary/70 rounded-full animate-pulse" style={{ width: '60%' }}></div>
                </div>
                <p className="text-sm text-muted-foreground mt-2">This may take a few moments...</p>
              </div>

              {/* Floating Elements */}
              <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-1/4 left-1/4 w-2 h-2 bg-primary/20 rounded-full animate-ping"></div>
                <div className="absolute top-1/3 right-1/3 w-1 h-1 bg-primary/30 rounded-full animate-ping" style={{ animationDelay: '1s' }}></div>
                <div className="absolute bottom-1/4 left-1/3 w-1.5 h-1.5 bg-primary/25 rounded-full animate-ping" style={{ animationDelay: '2s' }}></div>
                <div className="absolute bottom-1/3 right-1/4 w-1 h-1 bg-primary/20 rounded-full animate-ping" style={{ animationDelay: '3s' }}></div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* File Upload Area */}
      <Card className="border-dashed border-2 border-muted-foreground/25 bg-card/50 transition-colors duration-200">
        <CardContent className="p-8">
          <AnimatePresence mode="wait">
            {!selectedFile ? (
              <motion.div
                key="upload-area"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className={cn(
                  "flex flex-col items-center justify-center space-y-4 py-8 transition-colors duration-200",
                  isDragOver && "bg-primary/5 border-primary/50",
                )}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                <motion.div
                  animate={{
                    scale: isDragOver ? 1.1 : 1,
                    rotate: isDragOver ? 5 : 0,
                  }}
                  transition={{ duration: 0.2 }}
                  className={cn(
                    "rounded-full p-4 transition-colors duration-200",
                    isDragOver ? "bg-primary/10" : "bg-muted/50",
                  )}
                >
                  <Upload
                    className={cn(
                      "h-8 w-8 transition-colors duration-200",
                      isDragOver ? "text-primary" : "text-muted-foreground",
                    )}
                  />
                </motion.div>

                <div className="text-center space-y-2">
                  <h3 className="text-lg font-semibold">{isDragOver ? "Drop your PDF here" : "Upload PDF Document"}</h3>
                  <p className="text-sm text-muted-foreground">Drag and drop your PDF file here, or click to browse</p>
                  <p className="text-xs text-muted-foreground">Maximum file size: 10MB</p>
                </div>

                <Button variant="outline" className="relative overflow-hidden bg-transparent" onClick={handleBrowseClick}>
                  Browse Files
                </Button>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,application/pdf"
                  onChange={handleFileSelect}
                  className="hidden"
                />

                {error && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="flex items-center gap-2 text-destructive text-sm"
                  >
                    <AlertCircle className="h-4 w-4" />
                    {error}
                  </motion.div>
                )}
              </motion.div>
            ) : (
              <motion.div
                key="file-selected"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="space-y-4"
              >
                {/* File Preview */}
                {fileUrl && (
                  <div className="w-full overflow-auto rounded-lg border">
                    <div className="aspect-[11/7.4] w-full">
                      <embed 
                        src={`${fileUrl}#toolbar=0&navpanes=0&scrollbar=0`}
                        type="application/pdf" 
                        className="w-full h-full" 
                      />
                    </div>
                  </div>
                )}

                {/* File Info */}
                <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="rounded-full p-2 bg-primary/10">
                      <FileText className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <p className="font-medium text-sm">{selectedFile.name}</p>
                      <p className="text-xs text-muted-foreground">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button onClick={handleRemoveFile} variant="ghost" size="sm" className="h-8 w-8 p-0">
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>

                {/* Company and Jobsite Selector */}
                <CompanyJobsiteSelector 
                  onCompanySelect={handleCompanySelect}
                  onJobsiteSelect={handleJobsiteSelect}
                  onSelectionConfirmed={handleSelectionConfirmed}
                />


                {/* Upload Button */}
                <div className="flex items-center justify-between">
                  <Button variant="ghost" onClick={handleLogout} className="flex items-center gap-2">
                    <LogOut className="h-4 w-4" />
                    Sign Out
                  </Button>
                  {selectionConfirmed ? (
                    <Button 
                      onClick={uploadFileToDrive} 
                      disabled={uploading}
                      className="relative overflow-hidden bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70 text-white font-semibold px-8 py-3 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105 disabled:transform-none disabled:opacity-70"
                    >
                      {uploading ? (
                        <div className="flex items-center gap-3">
                          <div className="relative">
                            <div className="animate-spin rounded-full h-5 w-5 border-2 border-white/30"></div>
                            <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent absolute top-0 left-0"></div>
                          </div>
                          <span className="font-medium">Processing...</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <span className="font-semibold">Continue</span>
                          <svg 
                            className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-1" 
                            fill="none" 
                            stroke="currentColor" 
                            viewBox="0 0 24 24"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                          </svg>
                        </div>
                      )}
                      {/* Shine effect */}
                      <div className="absolute inset-0 -top-1 -left-1 bg-gradient-to-r from-transparent via-white/20 to-transparent transform -skew-x-12 -translate-x-full group-hover:translate-x-full transition-transform duration-1000"></div>
                    </Button>
                  ) : (
                    <div className="flex items-center gap-3 px-6 py-3 bg-muted/30 border border-muted-foreground/20 rounded-xl">
                      <div className="w-2 h-2 bg-muted-foreground/40 rounded-full animate-pulse"></div>
                      <span className="text-sm text-muted-foreground font-medium">
                        Complete project selection to continue
                      </span>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </CardContent>
      </Card>
    </div>
  )
}
