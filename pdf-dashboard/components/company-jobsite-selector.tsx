"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Loader2, Building2, MapPin, AlertCircle, Edit3, Check } from 'lucide-react'

interface CompanyJobsiteSelectorProps {
  onCompanySelect: (company: string) => void
  onJobsiteSelect: (jobsite: string) => void
  onSelectionConfirmed?: () => void
}

export function CompanyJobsiteSelector({ onCompanySelect, onJobsiteSelect, onSelectionConfirmed }: CompanyJobsiteSelectorProps) {
  const [selectedCompany, setSelectedCompany] = useState<string>('')
  const [selectedJobsite, setSelectedJobsite] = useState<string>('')
  const [companies, setCompanies] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [isCollapsed, setIsCollapsed] = useState(false)


  // Fetch companies from API
  useEffect(() => {
    const fetchCompanies = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await fetch('https://api.ttfconstruction.com/getCompanies.php')
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        
        const data = await response.json()
        
        // Filter out empty strings and clean up the data
        const cleanedCompanies = data
          .filter((company: string) => company && company.trim() !== '')
          .map((company: string) => company.trim())
          .sort() // Sort alphabetically
        
        setCompanies(cleanedCompanies)
      } catch (err) {
        setError('Failed to load companies. Please try again.')
      } finally {
        setLoading(false)
      }
    }

    fetchCompanies()
  }, [])

  const [jobsites, setJobsites] = useState<Array<{id: string, code: string, companyName: string, jobsite: string, contact: string, tel: string, email: string}>>([])
  const [loadingJobsites, setLoadingJobsites] = useState(false)

  const handleCompanyChange = async (companyName: string) => {
    setSelectedCompany(companyName)
    setSelectedJobsite('') // Reset jobsite when company changes
    setJobsites([]) // Clear previous jobsites
    
    onCompanySelect(companyName)
    
    // Fetch jobsites for the selected company
    if (companyName) {
      try {
        setLoadingJobsites(true)
        const response = await fetch(`https://api.ttfconstruction.com/getJobsitesPerCompany.php?company=${encodeURIComponent(companyName)}`)
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        
        const data = await response.json()
        setJobsites(data)
      } catch (err) {
        setError('Failed to load jobsites. Please try again.')
      } finally {
        setLoadingJobsites(false)
      }
    }
  }

  const handleJobsiteChange = (jobsiteId: string) => {
    setSelectedJobsite(jobsiteId)
    const jobsite = jobsites.find(j => j.id === jobsiteId)
    if (jobsite) {
      onJobsiteSelect(jobsite.jobsite || jobsite.code || `Jobsite ${jobsiteId}`)
    }
  }

  const getSelectedJobsiteDetails = () => {
    return jobsites.find(j => j.id === selectedJobsite)
  }

  const handleEdit = () => {
    setIsEditing(true)
    setIsCollapsed(false)
  }

  const handleConfirm = () => {
    setIsEditing(false)
    setIsCollapsed(true)
    onSelectionConfirmed?.() // Notify parent that selection is confirmed
  }

  const handleExpand = () => {
    setIsCollapsed(false)
    setIsEditing(true)
  }

  const isSelectionComplete = selectedCompany && selectedJobsite


  return (
    <Card className={`w-full border-2 hover:border-primary/20 transition-all duration-500 shadow-lg hover:shadow-xl ${isCollapsed ? 'shadow-md' : 'shadow-xl'}`}>
      <CardHeader className="pb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-primary/10 rounded-xl">
            <Building2 className="h-6 w-6 text-primary" />
          </div>
          <div>
            <CardTitle className="text-xl font-bold">Project Details</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Select your company and jobsite to get started
            </p>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {isCollapsed ? (
          /* Collapsed State */
          <div className="flex items-center justify-between p-4 bg-primary/5 rounded-lg border border-primary/20">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-primary/20 rounded-lg">
                  <Building2 className="h-4 w-4 text-primary" />
                </div>
                <span className="font-semibold text-sm">{selectedCompany}</span>
              </div>
              <div className="w-px h-6 bg-border"></div>
              <div className="flex items-center gap-2">
                <div className="p-2 bg-primary/20 rounded-lg">
                  <MapPin className="h-4 w-4 text-primary" />
                </div>
                <span className="font-semibold text-sm">
                  {getSelectedJobsiteDetails()?.jobsite || getSelectedJobsiteDetails()?.code || `Jobsite ${selectedJobsite}`}
                </span>
              </div>
            </div>
            <button
              onClick={handleExpand}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-primary hover:text-primary/80 hover:bg-primary/10 rounded-lg transition-all duration-200"
            >
              <Edit3 className="h-4 w-4" />
              Change
            </button>
          </div>
        ) : isEditing ? (
          /* Edit Mode - Selection Interface */
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Company Selection Column */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label htmlFor="company" className="text-base font-semibold">
                    Company
                  </Label>
                </div>
                
                <Select value={selectedCompany} onValueChange={handleCompanyChange} disabled={loading}>
                  <SelectTrigger className="h-14 border-2 hover:border-primary/30 transition-all duration-200 bg-background/50">
                    <div className="flex items-center gap-3">
                      {loading && <Loader2 className="h-5 w-5 animate-spin text-primary" />}
                      <SelectValue placeholder={loading ? "Loading companies..." : "Select a company"} />
                    </div>
                  </SelectTrigger>
                  <SelectContent className="max-h-60">
                    {loading ? (
                      <div className="flex items-center justify-center p-6">
                        <Loader2 className="h-6 w-6 animate-spin text-primary" />
                        <span className="ml-3 text-sm font-medium">Loading companies...</span>
                      </div>
                    ) : (
                      companies.map((company, index) => (
                        <SelectItem key={`${company}-${index}`} value={company} className="py-4">
                          <span className="font-medium">{company}</span>
                        </SelectItem>
                      ))
                    )}
                  </SelectContent>
                </Select>
                
                {error && (
                  <div className="flex items-center gap-3 p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
                    <AlertCircle className="h-5 w-5 text-destructive" />
                    <p className="text-sm text-destructive font-medium">{error}</p>
                  </div>
                )}
              </div>

              {/* Jobsite Selection Column */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label htmlFor="jobsite" className="text-base font-semibold">
                    Jobsite
                  </Label>
                  {selectedCompany && jobsites.length > 0 && (
                    <Badge variant="outline" className="text-xs px-2 py-1">
                      {jobsites.length} available
                    </Badge>
                  )}
                </div>
                
                <Select value={selectedJobsite} onValueChange={handleJobsiteChange} disabled={!selectedCompany || loadingJobsites}>
                  <SelectTrigger className="h-14 border-2 hover:border-primary/30 transition-all duration-200 bg-background/50">
                    <div className="flex items-center gap-3">
                      {loadingJobsites && <Loader2 className="h-5 w-5 animate-spin text-primary" />}
                      <SelectValue placeholder={
                        !selectedCompany 
                          ? "Select a company first" 
                          : loadingJobsites 
                            ? "Loading jobsites..." 
                            : "Select a jobsite"
                      } />
                    </div>
                  </SelectTrigger>
                  <SelectContent className="max-h-60">
                    {loadingJobsites ? (
                      <div className="flex items-center justify-center p-6">
                        <Loader2 className="h-6 w-6 animate-spin text-primary" />
                        <span className="ml-3 text-sm font-medium">Loading jobsites...</span>
                      </div>
                    ) : jobsites.length === 0 && selectedCompany ? (
                      <div className="flex flex-col items-center justify-center p-8 text-center">
                        <p className="text-sm text-muted-foreground font-medium">No jobsites found</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          This company doesn't have any jobsites available
                        </p>
                      </div>
                    ) : (
                      jobsites.map((jobsite) => (
                        <SelectItem key={jobsite.id} value={jobsite.id} className="py-4">
                          <div className="flex-1 min-w-0">
                            <div className="font-medium truncate">
                              {jobsite.jobsite || jobsite.code || `Jobsite ${jobsite.id}`}
                            </div>
                            {jobsite.contact && (
                              <div className="text-xs text-muted-foreground truncate">
                                Contact: {jobsite.contact}
                              </div>
                            )}
                          </div>
                        </SelectItem>
                      ))
                    )}
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            {/* Done Button for Edit Mode */}
            {isSelectionComplete && (
              <div className="flex justify-center pt-4">
                <button
                  onClick={() => setIsEditing(false)}
                  className="px-8 py-3 bg-primary text-primary-foreground rounded-xl font-semibold hover:bg-primary/90 transition-all duration-200 shadow-lg hover:shadow-xl"
                >
                  Done Editing
                </button>
              </div>
            )}
          </div>
        ) : !isSelectionComplete ? (
          /* Initial Selection Interface */
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Company Selection Column */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <Label htmlFor="company" className="text-base font-semibold">
                  Company
                </Label>
              </div>
              
              <Select value={selectedCompany} onValueChange={handleCompanyChange} disabled={loading}>
                <SelectTrigger className="h-14 border-2 hover:border-primary/30 transition-all duration-200 bg-background/50">
                  <div className="flex items-center gap-3">
                    {loading && <Loader2 className="h-5 w-5 animate-spin text-primary" />}
                    <SelectValue placeholder={loading ? "Loading companies..." : "Select a company"} />
                  </div>
                </SelectTrigger>
                <SelectContent className="max-h-60">
                  {loading ? (
                    <div className="flex items-center justify-center p-6">
                      <Loader2 className="h-6 w-6 animate-spin text-primary" />
                      <span className="ml-3 text-sm font-medium">Loading companies...</span>
                    </div>
                  ) : (
                    companies.map((company, index) => (
                      <SelectItem key={`${company}-${index}`} value={company} className="py-4">
                        <span className="font-medium">{company}</span>
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
              
              {error && (
                <div className="flex items-center gap-3 p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
                  <AlertCircle className="h-5 w-5 text-destructive" />
                  <p className="text-sm text-destructive font-medium">{error}</p>
                </div>
              )}
            </div>

            {/* Jobsite Selection Column */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <Label htmlFor="jobsite" className="text-base font-semibold">
                  Jobsite
                </Label>
                {selectedCompany && jobsites.length > 0 && (
                  <Badge variant="outline" className="text-xs px-2 py-1">
                    {jobsites.length} available
                  </Badge>
                )}
              </div>
              
              <Select value={selectedJobsite} onValueChange={handleJobsiteChange} disabled={!selectedCompany || loadingJobsites}>
                <SelectTrigger className="h-14 border-2 hover:border-primary/30 transition-all duration-200 bg-background/50">
                  <div className="flex items-center gap-3">
                    {loadingJobsites && <Loader2 className="h-5 w-5 animate-spin text-primary" />}
                    <SelectValue placeholder={
                      !selectedCompany 
                        ? "Select a company first" 
                        : loadingJobsites 
                          ? "Loading jobsites..." 
                          : "Select a jobsite"
                    } />
                  </div>
                </SelectTrigger>
                <SelectContent className="max-h-60">
                  {loadingJobsites ? (
                    <div className="flex items-center justify-center p-6">
                      <Loader2 className="h-6 w-6 animate-spin text-primary" />
                      <span className="ml-3 text-sm font-medium">Loading jobsites...</span>
                    </div>
                  ) : jobsites.length === 0 && selectedCompany ? (
                    <div className="flex flex-col items-center justify-center p-8 text-center">
                      <p className="text-sm text-muted-foreground font-medium">No jobsites found</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        This company doesn't have any jobsites available
                      </p>
                    </div>
                  ) : (
                    jobsites.map((jobsite) => (
                      <SelectItem key={jobsite.id} value={jobsite.id} className="py-4">
                        <div className="flex-1 min-w-0">
                          <div className="font-medium truncate">
                            {jobsite.jobsite || jobsite.code || `Jobsite ${jobsite.id}`}
                          </div>
                          {jobsite.contact && (
                            <div className="text-xs text-muted-foreground truncate">
                              Contact: {jobsite.contact}
                            </div>
                          )}
                        </div>
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>
          </div>
        ) : (
          /* Cool Selection Display */
          <div className="space-y-6">
            {/* Success Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 dark:bg-green-900/20 rounded-full">
                  <Check className="h-5 w-5 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-green-700 dark:text-green-300">Project Selected</h3>
                  <p className="text-sm text-muted-foreground">Ready to proceed with your selection</p>
                </div>
              </div>
              <button
                onClick={handleEdit}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-primary hover:text-primary/80 hover:bg-primary/5 rounded-lg transition-all duration-200"
              >
                <Edit3 className="h-4 w-4" />
                Edit
              </button>
            </div>

            {/* Selection Cards */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Company Card */}
              <div className="relative overflow-hidden rounded-xl border-2 border-primary/20 bg-gradient-to-br from-primary/5 to-primary/10 p-6">
                
                <div className="relative">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 bg-primary/20 rounded-lg">
                      <Building2 className="h-5 w-5 text-primary" />
                    </div>
                    <span className="text-sm font-medium text-primary/80 uppercase tracking-wide">Company</span>
                  </div>
                  <h4 className="text-xl font-bold text-foreground mb-2">{selectedCompany}</h4>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-sm text-muted-foreground">Active & Verified</span>
                  </div>
                </div>
              </div>

              {/* Jobsite Card */}
              <div className="relative overflow-hidden rounded-xl border-2 border-primary/20 bg-gradient-to-br from-primary/5 to-primary/10 p-6">
                
                <div className="relative">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 bg-primary/20 rounded-lg">
                      <MapPin className="h-5 w-5 text-primary" />
                    </div>
                    <span className="text-sm font-medium text-primary/80 uppercase tracking-wide">Jobsite</span>
                  </div>
                  <h4 className="text-xl font-bold text-foreground mb-2">
                    {getSelectedJobsiteDetails()?.jobsite || getSelectedJobsiteDetails()?.code || `Jobsite ${selectedJobsite}`}
                  </h4>
                  {getSelectedJobsiteDetails()?.contact && (
                    <div className="text-sm text-muted-foreground mb-2">
                      Contact: {getSelectedJobsiteDetails()?.contact}
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-sm text-muted-foreground">Ready for Processing</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Action Button */}
            <div className="flex justify-center pt-4">
              <button
                onClick={handleConfirm}
                className="px-8 py-3 bg-primary text-primary-foreground rounded-xl font-semibold hover:bg-primary/90 transition-all duration-200 shadow-lg hover:shadow-xl"
              >
                Continue with Selected Project
              </button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
