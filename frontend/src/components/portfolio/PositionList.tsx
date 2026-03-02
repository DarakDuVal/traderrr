"use client";

import type { PositionResponse } from "@traderrr/types";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Pencil, Trash2 } from "lucide-react";

interface PositionListProps {
  positions: PositionResponse[];
  onEdit: (position: PositionResponse) => void;
  onDelete: (position: PositionResponse) => void;
}

export function PositionList({ positions, onEdit, onDelete }: PositionListProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Ticker</TableHead>
          <TableHead>Shares</TableHead>
          <TableHead className="hidden sm:table-cell">Added</TableHead>
          <TableHead className="hidden md:table-cell">Updated</TableHead>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {positions.map((position) => (
          <TableRow key={position.id}>
            <TableCell className="font-medium">{position.ticker}</TableCell>
            <TableCell>{position.shares}</TableCell>
            <TableCell className="hidden sm:table-cell">{new Date(position.created_at).toLocaleDateString()}</TableCell>
            <TableCell className="hidden md:table-cell">{new Date(position.updated_at).toLocaleDateString()}</TableCell>
            <TableCell className="text-right">
              <div className="flex justify-end gap-1">
                <Button variant="ghost" size="icon" onClick={() => onEdit(position)} aria-label="Edit position">
                  <Pencil className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="icon" onClick={() => onDelete(position)} aria-label="Delete position">
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
