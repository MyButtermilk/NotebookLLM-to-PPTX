
import React from 'react'
import { render, screen } from '@testing-library/react'
import UploadZone from '../components/UploadZone'

describe('UploadZone', () => {
  it('renders upload text', () => {
    render(<UploadZone />)
    expect(screen.getByText(/Upload PDF to Convert/i)).toBeInTheDocument()
  })
})
